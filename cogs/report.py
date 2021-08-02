import copy
import typing
import re

import discord
from discord.ext import commands
from discord_components import InteractionType

import utils.globals as GG
from crawler_utilities.utils.pagination import BotEmbedPaginator
from models.milestone import Milestone, MilestoneException
from crawler_utilities.handlers import logger
from utils.checks import isManager, isAssignee, isReporter, isManagerAssigneeOrReporterButton
from utils.functions import get_settings
from models.reports import get_next_report_num, Report, ReportException, Attachment, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION, SHRUG_REACTION

log = logger.logger

REPORTS = []

BUG_RE = re.compile(r"\**What is the [Bb]ug\?\**:?\s?(.+?)(\n|$)")
FEATURE_RE = re.compile(r"\**Feature [Rr]equest\**:?\s?(.+?)(\n|$)")
MILESTONE_RE = re.compile(r"\**Milestone\**:?\s?(.+?)(\n|$)")

UPVOTE = "Upvote"
DOWNVOTE = "Downvote"
SHRUG = "Shrug"
INFORMATION = "Info"
SUBSCRIBE = "Subscribe"
RESOLVE = "Resolve"


def loop(result, error):
    if error:
        raise error
    elif result:
        REPORTS.append(result)


def getAllReports():
    collection = GG.MDB['Reports']
    cursor = collection.find()
    REPORTS.clear()
    cursor.each(callback=loop)
    return REPORTS


class ReportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    # LISTENERS

    @commands.Cog.listener()
    async def on_message(self, message):
        identifier = None
        repo = None
        channel = None
        is_bug = None
        type = None
        milestoneNotFound = None

        feature_match = FEATURE_RE.match(message.content)
        bug_match = BUG_RE.match(message.content)
        match = None

        for chan in GG.BUG_LISTEN_CHANS:
            if message.channel.id == chan['channel']:
                identifier = chan['identifier']
                repo = chan['repo']
                channel = chan['tracker']
                type = chan['type']

        if feature_match:
            if type == 'feature':
                match = feature_match
                is_bug = False
        elif bug_match:
            if type == 'bug':
                match = bug_match
                is_bug = True

        if match and identifier:
            title = match.group(1).strip(" *.\n")
            try:
                report_num = await get_next_report_num(identifier, message.guild.id)
            except ReportException as e:
                return await message.channel.send(e)

            report_id = f"{identifier}-{report_num}"
            attach = "\n" + '\n'.join(f"\n{'!' if item.url.lower().endswith(('.png', '.jpg', '.gif')) else ''}"
                                      f"[{item.filename}]({item.url})" for item in message.attachments)

            report = await Report.new(message.author.id, report_id, title,
                                      [Attachment(message.author.id, message.content + attach)], is_bug=is_bug,
                                      repo=repo, jumpUrl=message.jump_url, trackerId=channel)
            if is_bug:
                if message.guild.id in GG.SERVERS:
                    if repo is not None:
                        await report.setup_github(await self.bot.get_context(message), message.guild.id)

            reportMessage = await report.setup_message(self.bot, message.guild.id, report.trackerId)

            guild_settings = await get_settings(self.bot, message.guild.id)
            allow_milestoneAdding = guild_settings.get("allow_milestoneAdding", False)
            if allow_milestoneAdding:
                milestone_match = MILESTONE_RE.findall(message.content)
                if milestone_match is not None:
                    await report.commit()
                    matches = [x[0] for x in milestone_match]
                    _id = matches[0].strip(" *.\n")
                    try:
                        milestone = await Milestone.from_id(_id, message.guild.id)
                        await milestone.add_report(report_id, message.guild.id)
                        await milestone.notify_subscribers(self.bot, f"A new ticket was added to milestone `{_id}`.\nTicket: `{report_id}`")
                    except MilestoneException:
                        milestoneNotFound = f"Milestone {_id} not found, so couldn't add the report to it."
                else:
                    await report.commit()
            else:
                await report.commit()

            prefix = await self.bot.get_server_prefix(message)

            embed = discord.Embed()
            embed.title = f"Your submission ``{report_id} - {title}`` was accepted."
            embed.add_field(name="Status Checking", value=f"To check on its status: `{prefix}report {report_id}`.",
                            inline=False)
            embed.add_field(name="Note Adding",
                            value=f"To add a note, ie. when you forgot something, or want to add something later: `{prefix}note {report_id} <comment>`.",
                            inline=False)
            embed.add_field(name="Subscribing",
                            value=f"To subscribe to this ticket, so you get notified when changes are made: `{prefix}subscribe {report_id}`. (This is only for others, the submittee is automatically subscribed).",
                            inline=False)
            embed.add_field(name="Voting",
                            value=f"You can find your feature request/bug report here: [Click me]({reportMessage.jump_url})",
                            inline=False)
            if milestoneNotFound is not None:
                embed.add_field(name="Milestone Not Found", value=milestoneNotFound, inline=False)
            await message.channel.send(embed=embed)
            await message.add_reaction("\U00002705")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        if not event.guild_id:
            return

        msg_id = event.message_id
        server = self.bot.get_guild(event.guild_id)
        member = server.get_member(event.user_id)
        emoji = event.emoji

        await self.handle_reaction(msg_id, member, emoji, server)

    @commands.Cog.listener()
    async def on_button_click(self, res):
        label = res.component.label
        await self.handle_button(res.message, res.user, label, res.guild, res)

    # USER METHODS
    @commands.command(name="report")
    @commands.guild_only()
    async def viewreport(self, ctx, _id):
        """Gets the detailed status of a report."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.get_reportNotes(ctx)

    @commands.command(aliases=['cr'])
    @commands.guild_only()
    async def canrepro(self, ctx, _id, *, msg=''):
        """Adds reproduction to a report."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.canrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Added a note that you can reproduce this issue to `{report.report_id}` - {report.title}.", hidden=True)
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['up'])
    @commands.guild_only()
    async def upvote(self, ctx, _id, *, msg=''):
        """Adds an upvote to the selected feature request."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.upvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Added your upvote to `{report.report_id}` - {report.title}.", hidden=True)
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['cnr'])
    @commands.guild_only()
    async def cannotrepro(self, ctx, _id, *, msg=''):
        """Adds nonreproduction to a report."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.cannotrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Added a note that you cannot reproduce this issue to `{report.report_id}` - {report.title}.", hidden=True)
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['down'])
    @commands.guild_only()
    async def downvote(self, ctx, _id, *, msg=''):
        """Adds a downvote to the selected feature request."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.downvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Added your downvote to `{report.report_id}` - {report.title}.", hidden=True)
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['shrug'])
    @commands.guild_only()
    async def indifferent(self, ctx, _id, *, msg=''):
        """Adds a shrug to the selected feature request."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.indifferent(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Added your indifference to `{report.report_id}` - {report.title}.", hidden=True)
        await report.update(ctx, ctx.guild.id)

    @commands.command()
    @commands.guild_only()
    async def note(self, ctx, _id, *, msg=''):
        """Adds a note to a report."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.addnote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.reply(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['sub'])
    @commands.guild_only()
    async def subscribe(self, ctx, report_id):
        """Subscribes to a report."""
        report = await Report.from_id(report_id, ctx.guild.id)
        if ctx.message.author.id in report.subscribers:
            report.unsubscribe(ctx.message.author.id)
            await ctx.reply(f"OK, unsubscribed from `{report.report_id}` - {report.title}.", hidden=True)
        else:
            report.subscribe(ctx.message.author.id)
            await ctx.reply(f"OK, subscribed to `{report.report_id}` - {report.title}.", hidden=True)
        await report.commit()

    @commands.command()
    async def unsuball(self, ctx):
        """Unsubscribes from all reports."""
        reports = getAllReports()
        num_unsubbed = 0
        collection = GG.MDB['Reports']

        for report in reports:
            if ctx.message.author.id in report.get('subscribers', []):
                report['subscribers'].remove(ctx.message.author.id)
                num_unsubbed += 1
                await collection.replace_one({"report_id": report['report_id']}, report)

        await ctx.reply(f"OK, unsubscribed from {num_unsubbed} reports.", hidden=True)

    # Server Admins METHODS
    @commands.command(aliases=['close'])
    @commands.guild_only()
    async def resolve(self, ctx, _id, *, msg=''):
        """Server Admins only - Resolves a report."""
        report = await Report.from_id(_id, ctx.guild.id)
        if await isManager(ctx) or isAssignee(ctx, report) or await isReporter(ctx, report):
            await report.resolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.reply(f"Resolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['open'])
    @commands.guild_only()
    async def unresolve(self, ctx, _id, *, msg=''):
        """Server Admins only - Unresolves a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id, ctx.guild.id)
            await report.unresolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.reply(f"Unresolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['reassign'])
    @commands.guild_only()
    async def reidentify(self, ctx, report_id, identifier):
        """Server Admins only - Changes the identifier of a report."""
        if await isManager(ctx):
            identifier = identifier.upper()
            id_num = await get_next_report_num(identifier, ctx.guild.id)

            report = await Report.from_id(report_id, ctx.guild.id)
            new_report = copy.copy(report)
            await report.resolve(ctx, ctx.guild.id, f"Reassigned as `{identifier}-{id_num}`.", False)
            await report.commit()

            new_report.report_id = f"{identifier}-{id_num}"
            msg = await self.bot.get_channel(report.trackerId).send(embed=await new_report.get_embed())

            new_report.message = msg.id
            if new_report.github_issue:
                await new_report.update_labels()
                await new_report.edit_title(f"{new_report.report_id} {new_report.title}")
            await new_report.commit()
            await ctx.reply(f"Reassigned {report.report_id} as {new_report.report_id}.")

    @commands.command()
    @commands.guild_only()
    async def rename(self, ctx, report_id, *, name):
        """Server Admins only - Changes the title of a report."""
        if await isManager(ctx):
            report = await Report.from_id(report_id, ctx.guild.id)
            report.title = name
            if report.github_issue and report.repo is not None:
                await report.edit_title(f"{report.title}", f"{report.report_id} ")
            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.reply(f"Renamed {report.report_id} as {report.title}.")

    @commands.command(aliases=['pri'])
    @commands.guild_only()
    async def priority(self, ctx, _id, pri: int, *, msg=''):
        """Server Admins only - Changes the priority of a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id, ctx.guild.id)

            report.severity = pri
            if msg:
                await report.addnote(ctx.message.author.id, f"Priority changed to {pri} - {msg}", ctx, ctx.guild.id)

            if report.github_issue and report.repo is not None:
                await report.update_labels()

            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.reply(f"Changed priority of `{report.report_id}`: {report.title} to P{pri}.")

    @commands.command()
    @commands.guild_only()
    async def assign(self, ctx, _id, member: typing.Optional[discord.Member]):
        """Server Admins only - Changes the priority of a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id, ctx.guild.id)

            report.assignee = member.id

            await report.addnote(member.id, f"Assigned {report.report_id} to {member.mention}", ctx, ctx.guild.id)
            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.reply(f"Assigned {report.report_id} to {member.mention}")

    @commands.command()
    @commands.guild_only()
    async def assigned(self, ctx, member: typing.Optional[discord.Member]):
        if member is not None:
            if await isManager(ctx):
                await self.getAssignedReports(ctx, member)
            else:
                await ctx.reply("Only managers can request the assigned list for other people.")
        else:
            member = ctx.author
            await self.getAssignedReports(ctx, member)

    async def getAssignedReports(self, ctx, member):
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for listen in server['listen']:
            trackers.append(listen['tracker'])

        query = {"trackerId": {"$in": trackers}}
        reports = await GG.MDB.Reports.find(query).to_list(length=None)

        if len(reports) == 0:
            return await ctx.reply(f"No reports found.")

        assignedReports = []
        for report in reports:
            if member.id == report.get('assignee', []) and report['severity'] != -1:
                rep = {
                    "report_id": report['report_id'],
                    "title": report['title']
                }
                assignedReports.append(rep)

        if len(assignedReports) > 0:
            embedList = []
            for i in range(0, len(assignedReports), 10):
                lst = assignedReports[i:i + 10]
                desc = ""
                for item in lst:
                    desc += f'• `{item["report_id"]}` - {item["title"]}\n'
                if isinstance(member, discord.Member) and member.color != discord.Colour.default():
                    embed = discord.Embed(description=desc, color=member.color)
                else:
                    embed = discord.Embed(description=desc)
                embed.set_author(name=f'Assigned Reports for {member.mention}', icon_url=member.avatar_url)
                embedList.append(embed)

            paginator = BotEmbedPaginator(ctx, embedList)
            await paginator.run()
        else:
            await ctx.reply(f"{member.mention} doesn't have any assigned reports on this server.")


    @commands.command()
    @commands.guild_only()
    async def unassign(self, ctx, _id):
        """Server Admins only - Changes the priority of a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id, ctx.guild.id)

            report.assignee = None

            await report.addnote(ctx.message.author.id, f"Cleared assigned user from {report.report_id}", ctx,
                                 ctx.guild.id)
            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.reply(f"Cleared assigned user of {report.report_id}.")

    @commands.command()
    @commands.guild_only()
    async def merge(self, ctx, duplicate, mergeTo):
        """Server Admins only - Merges duplicate into mergeTo."""
        if await isManager(ctx):
            dupe = await Report.from_id(duplicate, ctx.guild.id)
            merge = await Report.from_id(mergeTo, ctx.guild.id)

            if dupe is not None and merge is not None:
                for x in dupe.attachments:
                    await merge.add_attachment(ctx, ctx.guild.id, x, False)

                await dupe.resolve(ctx, ctx.guild.id, f"Merged into {merge.report_id}")
                await dupe.commit()

                await merge.addnote(602779023151595546, f"Merged `{dupe.report_id}` into `{merge.report_id}`", ctx,
                                    ctx.guild.id, True)
                await merge.commit()
                await merge.update(ctx, ctx.guild.id)
                await ctx.reply(f"Merged `{dupe.report_id}` into `{merge.report_id}`")

    async def handle_reaction(self, msg_id, member, emoji, server):
        if emoji.name not in (UPVOTE_REACTION, DOWNVOTE_REACTION, INFORMATION_REACTION, SHRUG_REACTION):
            return

        try:
            report = await Report.from_message_id(msg_id)
        except ReportException:
            return

        if member.bot:
            return
        if report.is_bug:
            if emoji.name == INFORMATION_REACTION:
                print(f"Information: {member} - {report.report_id}")
                em = await report.get_embed(True)
                if member.dm_channel is not None:
                    DM = member.dm_channel
                else:
                    DM = await member.create_dm()
                try:
                    await DM.send(embed=em)
                except:
                    pass
            else:
                return

        if server.owner.id == member.id:
            if emoji.name == UPVOTE_REACTION:
                await report.force_accept(GG.ContextProxy(self.bot), server.id)
            elif emoji.name == INFORMATION_REACTION:
                em = await report.get_embed(True)
                if member.dm_channel is not None:
                    DM = member.dm_channel
                else:
                    DM = await member.create_dm()
                try:
                    await DM.send(embed=em)
                except:
                    pass
            else:
                log.info(f"Force denying {report.title}")
                await report.force_deny(GG.ContextProxy(self.bot), server.id)
                await report.commit()
                return
        else:
            try:
                if emoji.name == UPVOTE_REACTION:
                    print(f"Upvote: {member} - {report.report_id}")
                    await report.upvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                elif emoji.name == INFORMATION_REACTION:
                    print(f"Information: {member} - {report.report_id}")
                    em = await report.get_embed(True)
                    if member.dm_channel is not None:
                        DM = member.dm_channel
                    else:
                        DM = await member.create_dm()
                    try:
                        await DM.send(embed=em)
                    except:
                        pass
                elif emoji.name == SHRUG_REACTION:
                    print(f"Shrugged: {member} - {report.report_id}")
                    await report.indifferent(member.id, '', GG.ContextProxy(self.bot), server.id)
                else:
                    print(f"Downvote: {member} - {report.report_id}")
                    await report.downvote(member.id, '', GG.ContextProxy(self.bot), server.id)
            except ReportException as e:
                await member.send(str(e))

        await report.commit()
        await report.update(GG.ContextProxy(self.bot), server.id)

    async def handle_button(self, message, member, label, server, response):
        if label not in (UPVOTE, DOWNVOTE, INFORMATION, SHRUG, SUBSCRIBE, RESOLVE):
            return

        try:
            report = await Report.from_message_id(message.id)
        except ReportException:
            return

        if member.bot:
            return

        if report.is_bug:
            if label == INFORMATION:
                print(f"Information: {member} - {report.report_id}")
                em = await report.get_embed(True)
                await response.respond(embed=em)
            elif label == SUBSCRIBE:
                if member.id in report.subscribers:
                    report.unsubscribe(member.id)
                    await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have unsubscribed from {report.report_id}")
                else:
                    report.subscribe(member.id)
                    await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have subscribed to {report.report_id}")
            elif label == RESOLVE:
                if await isManagerAssigneeOrReporterButton(member.id, server.id, report, self.bot):
                    await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id, "Report closed.")
                    await report.commit()
                else:
                    await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You do not have permissions to resolve/close this.")
            else:
                return

        if not report.is_bug:
            if server.owner.id == member.id:
                if label == UPVOTE:
                    await report.force_accept(GG.ContextProxy(self.bot), server.id)
                    await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have accepted {report.report_id}")
                elif label == INFORMATION:
                    em = await report.get_embed(True)
                    await response.respond(embed=em)
                elif label == SHRUG:
                    pass
                elif label == SUBSCRIBE:
                    pass
                elif label == RESOLVE:
                    await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id, "Report closed.")
                    await report.commit()
                else:
                    log.info(f"Force denying {report.title}")
                    await report.force_deny(GG.ContextProxy(self.bot), server.id)
                    await report.commit()
            else:
                try:
                    if label == UPVOTE:
                        print(f"Upvote: {member} - {report.report_id}")
                        await report.upvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have upvoted {report.report_id}")
                    elif label == INFORMATION:
                        print(f"Information: {member} - {report.report_id}")
                        em = await report.get_embed(True)
                        await response.respond(embed=em)
                    elif label == SHRUG:
                        print(f"Shrugged: {member} - {report.report_id}")
                        await report.indifferent(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have shown indifference for {report.report_id}")
                    elif label == SUBSCRIBE:
                        if member.id in report.subscribers:
                            report.unsubscribe(member.id)
                            await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have unsubscribed from {report.report_id}")
                        else:
                            report.subscribe(member.id)
                            await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have subscribed to {report.report_id}")
                    elif label == RESOLVE:
                        if await isManagerAssigneeOrReporterButton(member.id, server.id, report, self.bot):
                            await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id, "Report closed.")
                            await report.commit()
                        else:
                            await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You do not have permissions to resolve/close this.")
                    else:
                        print(f"Downvote: {member} - {report.report_id}")
                        await report.downvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await response.respond(type=InteractionType.ChannelMessageWithSource, content=f"You have downvoted {report.report_id}")
                except ReportException as e:
                    if response.channel == message.channel:
                        await response.respond(type=InteractionType.ChannelMessageWithSource, content=str(e))
                    else:
                        await member.send(str(e))
                        await response.respond(type=6)

        if not response.responded:
            await response.respond(type=6)

        await report.commit()
        await report.update(GG.ContextProxy(self.bot), server.id)


def setup(bot):
    log.info("[Cogs] Report...")
    bot.add_cog(ReportCog(bot))
