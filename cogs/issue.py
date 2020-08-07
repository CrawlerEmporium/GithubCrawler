import copy
import typing
import re

import bson
import discord
from discord import NotFound
from discord.ext import commands
from discord.ext.commands import CommandInvokeError

import utils.globals as GG
from models.server import Server
from utils import logger, checks
from utils.libs.misc import ContextProxy
from utils.libs.reports import get_next_report_num, Report, ReportException, Attachment, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION

log = logger.logger

REPORTS = []

BUG_RE = re.compile(r"\**What is the [Bb]ug\?\**:?\s?(.+?)(\n|$)")
FEATURE_RE = re.compile(r"\**Feature [Rr]equest\**:?\s?(.+?)(\n|$)")


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


async def isManager(ctx):
    manager = await GG.MDB.Managers.find_one({"user": ctx.message.author.id, "server": ctx.guild.id})
    if manager is None:
        manager = False
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        if ctx.message.author.id == server['admin']:
            manager = True
    else:
        manager = True
    return manager


def isAssignee(ctx, report):
    if ctx.message.author.id == report.assignee:
        return True
    else:
        return False


class Issue(commands.Cog):
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
            report_num = await get_next_report_num(identifier, message.guild.id)
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        if not event.guild_id:
            return

        msg_id = event.message_id
        server = self.bot.get_guild(event.guild_id)
        member = server.get_member(event.user_id)
        emoji = event.emoji

        await self.handle_reaction(msg_id, member, emoji, server)

    # USER METHODS
    @commands.command(name="report")
    @commands.guild_only()
    async def viewreport(self, ctx, _id):
        """Gets the detailed status of a report."""
        report = await Report.from_id(_id)
        await report.get_reportNotes(ctx)

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
        report = await Report.from_id(_id)
        if await isManager(ctx) or isAssignee(ctx, report):
            await report.resolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.send(f"Resolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['open'])
    @commands.guild_only()
    async def unresolve(self, ctx, _id, *, msg=''):
        """Server Admins only - Unresolves a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id)
            await report.unresolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.send(f"Unresolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['reassign'])
    @commands.guild_only()
    async def reidentify(self, ctx, report_id, identifier):
        """Server Admins only - Changes the identifier of a report."""
        if await isManager(ctx):
            identifier = identifier.upper()
            id_num = await get_next_report_num(identifier, ctx.guild.id)

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
        if await isManager(ctx):
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
        if await isManager(ctx):
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
    async def assign(self, ctx, _id, member: typing.Optional[discord.Member] = None):
        """Server Admins only - Changes the priority of a report."""
        if await isManager(ctx):
            report = await Report.from_id(_id)

            report.assignee = member.id

            await report.addnote(member.id, f"Assigned {report.report_id} to {member.mention}", ctx, ctx.guild.id)
            await report.commit()
            await report.update(ctx, ctx.guild.id)
            await ctx.send(f"Assigned {report.report_id} to {member.mention}")

    @commands.command()
    @commands.guild_only()
    async def merge(self, ctx, duplicate, mergeTo):
        """Server Admins only - Merges duplicate into mergeTo."""
        if await isManager(ctx):
            dupe = await Report.from_id(duplicate)
            merge = await Report.from_id(mergeTo)

            if dupe is not None and merge is not None:
                for x in dupe.attachments:
                    await merge.add_attachment(ctx, ctx.guild.id, x, False)

                await dupe.resolve(ctx, ctx.guild.id, f"Merged into {merge.report_id}")
                await dupe.commit()

                await merge.addnote(602779023151595546, f"Merged `{dupe.report_id}` into `{merge.report_id}`", ctx,
                                    ctx.guild.id, True)
                await merge.commit()
                await merge.update(ctx, ctx.guild.id)
                await ctx.send(f"Merged `{dupe.report_id}` into `{merge.report_id}`")

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
