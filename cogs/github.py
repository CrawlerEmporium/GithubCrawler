import copy
import random
import re
import typing
import discord
from discord.ext import commands
import utils.globals as GG
from utils import logger

log = logger.logger

from utils.libs.github import GitHubClient
from utils.libs.jsondb import JSONDB
from utils.libs.misc import ContextProxy
from utils.libs.reports import get_next_report_num, Report, ReportException, Attachment, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION

ADMINS = [GG.OWNER, GG.GIDDY, GG.MPMB]

BUG_RE = re.compile(r"\**What is the [Bb]ug\?\**:?\s?(.+?)(\n|$)")
FEATURE_RE = re.compile(r"\**Feature [Rr]equest\**:?\s?(.+?)(\n|$)")


class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        identifier = None
        repo = None
        is_bug = None

        feature_match = FEATURE_RE.match(message.content)
        bug_match = BUG_RE.match(message.content)
        match = None

        if feature_match:
            match = feature_match
            is_bug = False
        elif bug_match:
            match = bug_match
            is_bug = True

        for chan in GG.BUG_LISTEN_CHANS:
            if message.channel.id == chan['id']:
                identifier = chan['identifier']
                repo = chan['repo']

        if match and identifier:
            title = match.group(1).strip(" *.\n")
            report_num = get_next_report_num(identifier)
            report_id = f"{identifier}-{report_num}"

            report = await Report.new(message.author.id, report_id, title,
                                      [Attachment(message.author.id, message.content)], is_bug=is_bug, repo=repo)
            if is_bug:
                await report.setup_github(await self.bot.get_context(message), message.guild.id)

            await report.setup_message(self.bot, message.guild.id)
            report.commit()
            await message.add_reaction(random.choice(GG.REACTIONS))

    # USER METHODS

    @commands.command(name="report")
    async def viewreport(self, ctx, _id):
        """Gets the detailed status of a report."""
        await ctx.send(embed=Report.from_id(_id).get_embed(True, ctx))

    @commands.command(aliases=['cr'])
    async def canrepro(self, ctx, _id, *, msg=''):
        """Adds reproduction to a report."""
        report = Report.from_id(_id)
        await report.canrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['up'])
    async def upvote(self, ctx, _id, *, msg=''):
        """Adds an upvote to the selected feature request."""
        report = Report.from_id(_id)
        await report.upvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['cnr'])
    async def cannotrepro(self, ctx, _id, *, msg=''):
        """Adds nonreproduction to a report."""
        report = Report.from_id(_id)
        await report.cannotrepro(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['down'])
    async def downvote(self, ctx, _id, *, msg=''):
        """Adds a downvote to the selected feature request."""
        report = Report.from_id(_id)
        await report.downvote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command()
    async def note(self, ctx, _id, *, msg=''):
        """Adds a note to a report."""
        report = Report.from_id(_id)
        await report.addnote(ctx.message.author.id, msg, ctx, ctx.guild.id)
        # report.subscribe(ctx)
        report.commit()
        await ctx.send(f"Ok, I've added a note to `{report.report_id}` - {report.title}.")
        await report.update(ctx, ctx.guild.id)

    @commands.command(aliases=['sub'])
    async def subscribe(self, ctx, report_id):
        """Subscribes to a report."""
        report = Report.from_id(report_id)
        if ctx.message.author.id in report.subscribers:
            report.unsubscribe(ctx)
            await ctx.send(f"OK, unsubscribed from `{report.report_id}` - {report.title}.")
        else:
            report.subscribe(ctx)
            await ctx.send(f"OK, subscribed to `{report.report_id}` - {report.title}.")
        report.commit()

    @commands.command()
    async def unsuball(self, ctx):
        """Unsubscribes from all reports."""
        reports = self.bot.db.jget("reports", {})
        num_unsubbed = 0

        for _id, report in reports.items():
            if ctx.message.author.id in report.get('subscribers', []):
                report['subscribers'].remove(ctx.message.author.id)
                num_unsubbed += 1
                reports[_id] = report

        self.bot.db.jset("reports", reports)
        await ctx.send(f"OK, unsubscribed from {num_unsubbed} reports.")

    # OWNER METHODS
    @commands.command(aliases=['close'])
    async def resolve(self, ctx, _id, *, msg=''):
        """Owner only - Resolves a report."""
        if not ctx.message.author.id in ADMINS:
            return
        report = Report.from_id(_id)
        await report.resolve(ctx, ctx.guild.id, msg)
        report.commit()
        await ctx.send(f"Resolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['open'])
    async def unresolve(self, ctx, _id, *, msg=''):
        """Owner only - Unresolves a report."""
        if not ctx.message.author.id in ADMINS:
            return
        report = Report.from_id(_id)
        await report.unresolve(ctx, ctx.guild.id, msg)
        report.commit()
        await ctx.send(f"Unresolved `{report.report_id}`: {report.title}.")

    @commands.command(aliases=['reassign'])
    async def reidentify(self, ctx, report_id, identifier):
        """Owner only - Changes the identifier of a report."""
        if not ctx.message.author.id in ADMINS:
            return

        identifier = identifier.upper()
        id_num = get_next_report_num(identifier)

        report = Report.from_id(report_id)
        new_report = copy.copy(report)
        await report.resolve(ctx, ctx.guild.id, f"Reassigned as `{identifier}-{id_num}`.", False)
        report.commit()

        new_report.report_id = f"{identifier}-{id_num}"
        if ctx.guild.id == GG.GUILD:
            msg = await self.bot.get_channel(GG.TRACKER_CHAN_5ET).send(embed=new_report.get_embed())
        elif ctx.guild.id == 533350585706217494:
            msg = await self.bot.get_channel(GG.TRACKER_CHAN_MPMB).send(embed=new_report.get_embed())
        else:
            msg = await self.bot.get_channel(GG.TRACKER_CHAN).send(embed=new_report.get_embed())

        new_report.message = msg.id
        if new_report.github_issue:
            await new_report.update_labels()
            await new_report.edit_title(f"{new_report.report_id} {new_report.title}")
        new_report.commit()
        await ctx.send(f"Reassigned {report.report_id} as {new_report.report_id}.")

    @commands.command()
    async def rename(self, ctx, report_id, *, name):
        """Owner only - Changes the title of a report."""
        if not ctx.message.author.id in ADMINS:
            return

        report = Report.from_id(report_id)
        report.title = name
        if report.github_issue:
            await report.edit_title(f"{report.report_id} {report.title}")
        report.commit()
        await report.update(ctx, ctx.guild.id)
        await ctx.send(f"Renamed {report.report_id} as {report.title}.")

    @commands.command(aliases=['pri'])
    async def priority(self, ctx, _id, pri: int, *, msg=''):
        """Owner only - Changes the priority of a report."""
        if not ctx.message.author.id in ADMINS:
            return
        report = Report.from_id(_id)

        report.severity = pri
        if msg:
            await report.addnote(ctx.message.author.id, f"Priority changed to {pri} - {msg}", ctx, ctx.guild.id)

        if report.github_issue:
            await report.update_labels()

        report.commit()
        await report.update(ctx, ctx.guild.id)
        await ctx.send(f"Changed priority of `{report.report_id}`: {report.title} to P{pri}.")

    @commands.command(aliases=['pend'])
    async def pending(self, ctx, *reports):
        """Owner only - Marks reports as pending for next patch."""
        if not ctx.message.author.id in ADMINS:
            return
        not_found = 0
        for _id in reports:
            try:
                report = Report.from_id(_id)
            except ReportException:
                not_found += 1
                continue
            report.pend()
            report.commit()
            await report.update(ctx, ctx.guild.id)
        if not not_found:
            await ctx.send(f"Marked {len(reports)} reports as patch pending.")
        else:
            await ctx.send(f"Marked {len(reports)} reports as patch pending. {not_found} reports were not found.")

    @commands.command()
    async def update(self, ctx, build_id, *, msg=""):
        """Owner only - To be run after an update. Resolves all -P2 reports."""
        if not ctx.message.author.id in ADMINS:
            return
        changelog = ""
        for _id in list(set(self.bot.db.jget("pending-reports", []))):
            report = Report.from_id(_id)
            await report.resolve(ctx, ctx.guild.id, f"Patched in build {build_id}", ignore_closed=True)
            report.commit()
            action = "Fixed"
            if not report.is_bug:
                action = "Added"
            if report.get_issue_link():
                changelog += f"- {action} [`{report.report_id}`]({report.get_issue_link()}) {report.title}\n"
            else:
                changelog += f"- {action} `{report.report_id}` {report.title}\n"
        changelog += msg

        self.bot.db.jset("pending-reports", [])
        await ctx.send(embed=discord.Embed(title=f"**Build {build_id}**", description=changelog, colour=0x87d37c))
        await ctx.message.delete()

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
            report = Report.from_message_id(msg_id)
        except ReportException:
            return

        if report.is_bug:
            return
        if member.bot:
            return

        if member.id == GG.GIDDY or member.id == GG.OWNER or member.id == GG.MPMB:
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
                print(f"Force denying {report.title}")
                await report.force_deny(ContextProxy(self.bot), server.id)
                report.commit()
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
        # if member.id not in report.subscribers:
        #     report.subscribers.append(member.id)
        report.commit()
        await report.update(ContextProxy(self.bot), server.id)


def setup(bot):
    log.info("Loading Github Cog...")
    bot.add_cog(Github(bot))
