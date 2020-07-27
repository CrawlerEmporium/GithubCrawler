import copy
import decimal
import random
import re

import bson
from discord import NotFound
from discord.ext import commands
from discord.ext.commands import CommandInvokeError

import utils.globals as GG
from models.server import Server
from utils import logger
from utils.libs.misc import ContextProxy
from utils.libs.reports import get_next_report_num, Report, ReportException, Attachment, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION

log = logger.logger

REPORTS = []

BUG_RE = re.compile(r"\**What is the [Bb]ug\?\**:?\s?(.+?)(\n|$)")
FEATURE_RE = re.compile(r"\**Feature [Rr]equest\**:?\s?(.+?)(\n|$)")


async def round_down(value, decimals):
    with decimal.localcontext() as ctx:
        d = decimal.Decimal(value)
        ctx.rounding = decimal.ROUND_DOWN
        return round(d, decimals)


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


def checkUserVsAdmin(server, member):
    User = {"guild": server, "user": member}
    wanted = next((item for item in GG.GITHUBSERVERS if item.server == server), None)
    if wanted is not None:
        Server = {"guild": wanted.server, "user": wanted.admin}
        if User == Server:
            return True
    return False


class Issue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @commands.Cog.listener()
    async def on_message(self, message):
        identifier = None
        repo = None
        channel = None
        is_bug = None
        type = None

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
            report_num = await get_next_report_num(identifier)
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

            await report.setup_message(self.bot, message.guild.id, report.trackerId)
            await report.commit()
            await message.add_reaction("\U00002705")

    # USER METHODS
    @commands.command(name="report")
    @commands.guild_only()
    async def viewreport(self, ctx, _id):
        """Gets the detailed status of a report."""
        report = await Report.from_id(_id)
        await ctx.send(embed=report.get_embed(True, ctx))

    @commands.command(aliases=['cr'])
    @commands.guild_only()
    async def canrepro(self, ctx, _id, *, msg=''):
        """Adds reproduction to a report."""
        report = await Report.from_id(_id)
        await report.canrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['up'])
    @commands.guild_only()
    async def upvote(self, ctx, _id, *, msg=''):
        """Adds an upvote to the selected feature request."""
        report = await Report.from_id(_id)
        await report.upvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['cnr'])
    @commands.guild_only()
    async def cannotrepro(self, ctx, _id, *, msg=''):
        """Adds nonreproduction to a report."""
        report = await Report.from_id(_id)
        await report.cannotrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['down'])
    @commands.guild_only()
    async def downvote(self, ctx, _id, *, msg=''):
        """Adds a downvote to the selected feature request."""
        report = await Report.from_id(_id)
        await report.downvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command()
    @commands.guild_only()
    async def note(self, ctx, _id, *, msg=''):
        """Adds a note to a report."""
        report = await Report.from_id(_id)
        await report.addnote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        await report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['sub'])
    @commands.guild_only()
    async def subscribe(self, ctx, report_id):
        """Subscribes to a report."""
        report = await Report.from_id(report_id)
        if ctx.message.author.id in report.subscribers:
            report.unsubscribe(ctx)
            await ctx.send(f"OK, unsubscribed from `{report.report_id}` - {report.title}.")
        else:
            report.subscribe(ctx)
            await ctx.send(f"OK, subscribed to `{report.report_id}` - {report.title}.")
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

        await ctx.send(f"OK, unsubscribed from {num_unsubbed} reports.")

    # Server Admins METHODS
    @commands.command(aliases=['close'])
    @commands.guild_only()
    async def resolve(self, ctx, _id, *, msg=''):
        """Server Admins only - Resolves a report."""
        if not ctx.message.author.id in GG.ADMINS:
            return
        if checkUserVsAdmin(ctx.guild.id, ctx.message.author.id):
            report = await Report.from_id(_id)
            await report.resolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.send(f"Resolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['open'])
    @commands.guild_only()
    async def unresolve(self, ctx, _id, *, msg=''):
        """Server Admins only - Unresolves a report."""
        if not ctx.message.author.id in GG.ADMINS:
            return
        if checkUserVsAdmin(ctx.guild.id, ctx.message.author.id):
            report = await Report.from_id(_id)
            await report.unresolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.send(f"Unresolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['reassign'])
    @commands.guild_only()
    async def reidentify(self, ctx, report_id, identifier):
        """Server Admins only - Changes the identifier of a report."""
        if not ctx.message.author.id in GG.ADMINS:
            return
        if checkUserVsAdmin(ctx.guild.id, ctx.message.author.id):
            identifier = identifier.upper()
            id_num = await get_next_report_num(identifier)

            report = await Report.from_id(report_id)
            new_report = copy.copy(report)
            await report.resolve(ctx, ctx.guild.id, f"Reassigned as `{identifier}-{id_num}`.", False)
            await report.commit()

            new_report.report_id = f"{identifier}-{id_num}"
            msg = await self.bot.get_channel(report.trackerId).send(embed=new_report.get_embed())

            new_report.message = msg.id
            if new_report.github_issue:
                await new_report.update_labels()
                await new_report.edit_title(f"{new_report.report_id} {new_report.title}")
            await new_report.commit()
            await ctx.send(f"Reassigned {report.report_id} as {new_report.report_id}.")

    @commands.command()
    @commands.guild_only()
    async def rename(self, ctx, report_id, *, name):
        """Server Admins only - Changes the title of a report."""
        if not ctx.message.author.id in GG.ADMINS:
            return
        if checkUserVsAdmin(ctx.guild.id, ctx.message.author.id):
            report = await Report.from_id(report_id)
            report.title = name
            if report.github_issue and report.repo is not None:
                await report.edit_title(f"{report.title}", f"{report.report_id} ")
            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.send(f"Renamed {report.report_id} as {report.title}.")

    @commands.command(aliases=['pri'])
    @commands.guild_only()
    async def priority(self, ctx, _id, pri: int, *, msg=''):
        """Server Admins only - Changes the priority of a report."""
        if not ctx.message.author.id in GG.ADMINS:
            return
        if checkUserVsAdmin(ctx.guild.id, ctx.message.author.id):
            report = await Report.from_id(_id)

            report.severity = pri
            if msg:
                await report.addnote(ctx.message.author.id, f"Priority changed to {pri} - {msg}", ctx, ctx.guild.id)

            if report.github_issue and report.repo is not None:
                await report.update_labels()

            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.send(f"Changed priority of `{report.report_id}`: {report.title} to P{pri}.")

    @commands.command()
    @commands.guild_only()
    async def top(self, ctx, top=10):
        """Gets top x or top 10"""
        reports = await GG.MDB.Reports.find({}).to_list(length=None)
        serverReports = []

        if ctx.guild.id == 363680385336606740:
            return await self.GUILDTFLOP(ctx, reports, top)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.guild.id)
            server = guild.listen[0].repo
        except:
            await ctx.send("Your server isn't registered yet.")
            return

        if server is not None:
            for report in reports:
                repo = report.get('github_repo', None)
                if server == repo:
                    if report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            "upvotes": report['upvotes']
                        }
                        serverReports.append(rep)
        else:
            trackerChannels = []
            for x in guild.listen:
                trackerChannels.append(x.tracker)
            for report in reports:
                tracker = report.get('trackerId', None)
                if tracker in trackerChannels:
                    if report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            "upvotes": report['upvotes']
                        }
                        serverReports.append(rep)

        sortedList = sorted(serverReports, key=lambda k: k['upvotes'], reverse=True)
        embed = GG.EmbedWithAuthor(ctx)
        if top <= 0:
            top = 10
        if top >= 25:
            top = 25
        embed.title = f"Top {top} most upvoted suggestions."
        i = 1
        for report in sortedList[:top]:
            embed.add_field(name=f"**#{i} - {report['upvotes']}** upvotes",
                            value=f"{report['report_id']}: {report['title']}", inline=False)
            i += 1
        await ctx.send(embed=embed)


    async def GUILDTFLOP(self, ctx, reports, top, flop=False):
        async with ctx.channel.typing():
            BOOSTERMEMBERS = [x.id for x in ctx.guild.get_role(585540203704483860).members]
            T2MEMBERS = [x.id for x in ctx.guild.get_role(606989073453678602).members]
            T3MEMBERS = [x.id for x in ctx.guild.get_role(606989264051503124).members]
            serverReports = []
            toolsReports = []
            for report in reports:
                if "5etools/tracker" in report.get('github_repo', []):
                    toolsReports.append(report)
            if flop:
                msg = await ctx.send(f"Checking {len(toolsReports)} suggestions for their downvotes...")
            else:
                msg = await ctx.send(f"Checking {len(toolsReports)} suggestions for their upvotes...")
            for report in toolsReports:
                if report['severity'] != -1:
                    attachments = report['attachments']
                    upvotes = 0
                    downvotes = 0
                    for attachment in attachments:
                        if attachment['veri'] == -2:
                            try:
                                if attachment['author'] in BOOSTERMEMBERS:
                                    downvotes += 1
                                if attachment['author'] in T2MEMBERS:
                                    downvotes += 1
                                if attachment['author'] in T3MEMBERS:
                                    downvotes += 2
                                downvotes += 1
                            except NotFound:
                                downvotes += 1
                        if attachment['veri'] == 2:
                            try:
                                if attachment['author'] in BOOSTERMEMBERS:
                                    upvotes += 1
                                if attachment['author'] in T2MEMBERS:
                                    upvotes += 1
                                if attachment['author'] in T3MEMBERS:
                                    upvotes += 2
                                upvotes += 1
                            except NotFound:
                                upvotes += 1
                    rep = {
                        "report_id": report['report_id'],
                        "title": report['title'],
                        "upvotes": upvotes,
                        "downvotes": downvotes,
                        "message": report['message'],
                        "rating": (0 - downvotes) + upvotes,
                        "total": downvotes + upvotes
                    }
                    serverReports.append(rep)
            if flop:
                sortedList = sorted(serverReports, key=lambda k: k['rating'], reverse=False)
            else:
                sortedList = sorted(serverReports, key=lambda k: k['rating'], reverse=True)
            embed = GG.EmbedWithAuthor(ctx)
            if top <= 0:
                top = 10
            if top >= 25:
                top = 25
            if flop:
                embed.title = f"Top {top} most downvoted suggestions."
            else:
                embed.title = f"Top {top} most upvoted suggestions."
            i = 1
            channel = await ctx.bot.fetch_channel(593769144969723914)
            for report in sortedList[:top]:
                try:
                    message = await channel.fetch_message(report['message'])
                    msg_url = f"[Link]({message.jump_url})"
                except:
                    msg_url = f"No Link"

                perc = 100 * float(report['upvotes']) / float(report['total'])
                percRounded = await round_down(perc, 2)

                embed.add_field(name=f"**#{i} - {report['rating']}** points ({str(percRounded)}% upvotes)",
                                value=f"{report['report_id']}: {report['title']} - {msg_url}", inline=False)
                i += 1
            await msg.edit(embed=embed, content="")
            return

    @commands.command()
    @commands.guild_only()
    async def flop(self, ctx, top=10):
        """Gets top x or top 10"""
        # -2 in attachment
        reports = await GG.MDB.Reports.find({}).to_list(length=None)
        serverReports = []

        if ctx.guild.id == 363680385336606740:
            return await self.GUILDTFLOP(ctx, reports, top, flop=True)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.guild.id)
            server = guild.listen[0].repo
        except:
            await ctx.send("Your server isn't registered yet.")
            return

        if server is not None:
            for report in reports:
                repo = report.get('github_repo', None)
                if server == repo:
                    if int(report['downvotes']) >= 1 and report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            "downvotes": report['downvotes']
                        }
                        serverReports.append(rep)
        else:
            trackerChannels = []
            for x in guild.listen:
                trackerChannels.append(x.tracker)
            for report in reports:
                tracker = report.get('trackerId', None)
                if tracker in trackerChannels:
                    if int(report['downvotes']) >= 1 and report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            "downvotes": report['downvotes']
                        }
                        serverReports.append(rep)

        sortedList = sorted(serverReports, key=lambda k: k['downvotes'], reverse=True)
        embed = GG.EmbedWithAuthor(ctx)
        if top <= 0:
            top = 10
        if top >= 25:
            top = 25
        embed.title = f"Top {top} most downvoted suggestions."
        i = 1
        for report in sortedList[:top]:
            embed.add_field(name=f"**#{i} - {report['downvotes']}** downvotes",
                            value=f"{report['report_id']}: {report['title']}", inline=False)
            i += 1
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        if not event.guild_id:
            return

        msg_id = event.message_id
        server = self.bot.get_guild(event.guild_id)
        member = server.get_member(event.user_id)
        emoji = event.emoji

        await self.handle_reaction(msg_id, member, emoji, server)

    async def handle_reaction(self, msg_id, member, emoji, server):
        if emoji.name not in (UPVOTE_REACTION, DOWNVOTE_REACTION, INFORMATION_REACTION):
            return

        try:
            report = await Report.from_message_id(msg_id)
        except ReportException:
            return

        if report.is_bug:
            return
        if member.bot:
            return

        if checkUserVsAdmin(server.id, member.id):
            if emoji.name == UPVOTE_REACTION:
                await report.force_accept(ContextProxy(self.bot), server.id)
            elif emoji.name == INFORMATION_REACTION:
                em = report.get_embed(True)
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
                await report.force_deny(ContextProxy(self.bot), server.id)
                await report.commit()
                return
        else:
            try:
                if emoji.name == UPVOTE_REACTION:
                    print(f"Upvote: {member} - {report.report_id}")
                    await report.upvote(member.id, '', ContextProxy(self.bot), server.id)
                elif emoji.name == INFORMATION_REACTION:
                    print(f"Information: {member} - {report.report_id}")
                    em = report.get_embed(True)
                    if member.dm_channel is not None:
                        DM = member.dm_channel
                    else:
                        DM = await member.create_dm()
                    try:
                        await DM.send(embed=em)
                    except:
                        pass
                else:
                    print(f"Downvote: {member} - {report.report_id}")
                    await report.downvote(member.id, '', ContextProxy(self.bot), server.id)
            except ReportException as e:
                await member.send(str(e))

        await report.commit()
        await report.update(ContextProxy(self.bot), server.id)


def setup(bot):
    log.info("[Cogs] Issue...")
    bot.add_cog(Issue(bot))
