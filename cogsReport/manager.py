import copy

import discord
from discord import slash_command, Option, permissions
from discord.ext import commands

import utils.globals as GG
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.handlers import logger
from crawler_utilities.utils.pagination import BotEmbedPaginator
from models.reports import Report, get_next_report_num
from utils.autocomplete import get_server_reports, get_server_identifiers
from utils.checks import isManager, isAssignee, isReporter
from utils.reportglobals import ReportFromId

log = logger.logger


class ManagerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="resolve")
    @permissions.guild_only()
    async def resolve(self, ctx, _id: Option(str, "Which report do you want to resolve?", autocomplete=get_server_reports), msg: Option(str, "Optional resolve comment", default="")):
        """Server Admins only - Resolves a report."""
        await ctx.defer()
        report = await ReportFromId(_id, ctx)
        if await isManager(ctx) or isAssignee(ctx, report) or await isReporter(ctx, report):
            await report.resolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.respond(f"Resolved `{report.report_id}`: {report.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="unresolve")
    @permissions.guild_only()
    async def unresolve(self, ctx, _id: Option(str, "Which report do you want to unresolve?", autocomplete=get_server_reports), msg: Option(str, "Optional unresolve comment", default="")):
        """Server Admins only - Unresolves a report."""
        await ctx.defer()
        if await isManager(ctx):
            report = await ReportFromId(_id, ctx)
            await report.unresolve(ctx, ctx.guild.id, msg)
            await report.commit()
            await ctx.respond(f"Unresolved `{report.report_id}`: {report.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="reidentify")
    @permissions.guild_only()
    async def reidentify(self, ctx, _id: Option(str, "Which report do you want to reidentify?", autocomplete=get_server_reports), identifier: Option(str, "To which identifier do you want to change this report?", autocomplete=get_server_identifiers)):
        """Server Admins only - Changes the identifier of a report."""
        await ctx.defer()
        if await isManager(ctx):
            identifier = identifier.upper()
            id_num = await get_next_report_num(identifier, ctx.interaction.guild.id)

            report = await ReportFromId(_id, ctx)
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
            await ctx.respond(f"Reassigned {report.report_id} as {new_report.report_id}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="rename")
    @permissions.guild_only()
    async def rename(self, ctx, _id: Option(str, "Which report do you want to rename?", autocomplete=get_server_reports), name: Option(str, "The new title for the report")):
        """Server Admins only - Changes the title of a report."""
        await ctx.defer()
        if await isManager(ctx):
            report = await ReportFromId(_id, ctx)
            report.title = name
            if report.github_issue and report.repo is not None:
                await report.edit_title(f"{report.title}", f"{report.report_id} ")
            await report.commit()
            await report.update(ctx, ctx.interaction.guild.id)
            await ctx.respond(f"Renamed {report.report_id} as {report.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    # @slash_command(name="priority")
    # async def priority(self, ctx, _id, pri: int, *, msg=''):
    #     """Server Admins only - Changes the priority of a report."""
    #     if await isManager(ctx):
    #         report = await ReportFromId(_id, ctx)
    #
    #         report.severity = pri
    #         if msg:
    #             await report.addnote(ctx.message.author.id, f"Priority changed to {pri} - {msg}", ctx, ctx.guild.id)
    #
    #         if report.github_issue and report.repo is not None:
    #             await report.update_labels()
    #
    #         await report.commit()
    #         await report.update(ctx, ctx.guild.id)
    #         await ctx.respond(f"Changed priority of `{report.report_id}`: {report.title} to P{pri}.")
    #     else:
    #         await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="assign")
    @permissions.guild_only()
    async def assign(self, ctx, member: Option(discord.Member, "What user do you want to assign?"), _id: Option(str, "To which report do you want to assign the user?", autocomplete=get_server_reports)):
        """Server Admins only - Assign a member to a report."""
        await ctx.defer()
        if await isManager(ctx):
            report = await ReportFromId(_id, ctx)
            track_google_analytics_event("Assign", f"{report.report_id}", f"{ctx.interaction.user.id}")

            report.assignee = member.id

            await report.addnote(ctx.interaction.user.id, f"Assigned {report.report_id} to {member.mention}", ctx, ctx.interaction.guild_id)
            await report.commit()
            await report.update(ctx, ctx.interaction.guild_id)
            await ctx.respond(f"Assigned {report.report_id} to {member.mention}")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="assigned")
    @permissions.guild_only()
    async def assigned(self, ctx, member: Option(discord.Member, "For which user?")):
        """Get a list of assigned reports from a member. (or yourself)"""
        await ctx.defer()
        if member is not None:
            if await isManager(ctx):
                await self.getAssignedReports(ctx, member)
            else:
                await ctx.respond("Only managers can request the assigned list for other people.")
        else:
            member = ctx.author
            await self.getAssignedReports(ctx, member)

    async def getAssignedReports(self, ctx, member):
        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild.id})
        trackers = []
        for listen in server['listen']:
            trackers.append(listen['tracker'])

        query = {"trackerId": {"$in": trackers}}
        reports = await GG.MDB.Reports.find(query).to_list(length=None)

        if len(reports) == 0:
            return await ctx.respond(f"No reports found.")

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
                embed.set_author(name=f'Assigned open tickets for {member.nick if member.nick is not None else member.name}', icon_url=member.display_avatar.url)
                embedList.append(embed)

            paginator = BotEmbedPaginator(ctx, embedList)
            await paginator.run()
        else:
            await ctx.respond(f"{member.mention} doesn't have any assigned reports on this server.")

    @slash_command(name="unassign")
    @permissions.guild_only()
    async def unassign(self, ctx, _id: Option(str, "Unassign everyone from this report", autocomplete=get_server_reports)):
        """Server Admins only - Unassign a member from a report."""
        await ctx.defer()
        if await isManager(ctx):
            report = await ReportFromId(_id, ctx)
            track_google_analytics_event("Unassign", f"{report.report_id}", f"{ctx.interaction.user.id}")

            report.assignee = None

            await report.addnote(ctx.interaction.user.id, f"Cleared assigned user from {report.report_id}", ctx,
                                 ctx.interaction.guild.id)
            await report.commit()
            await report.update(ctx, ctx.interaction.guild.id)
            await ctx.respond(f"Cleared assigned user of {report.report_id}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="merge")
    @permissions.guild_only()
    async def merge(self, ctx, duplicate: Option(str, "Duped report", autocomplete=get_server_reports), merger: Option(str, "Merge into this report", autocomplete=get_server_reports)):
        """Server Admins only - Merges duplicate into mergeTo."""
        await ctx.defer()
        if await isManager(ctx):
            dupe = await ReportFromId(duplicate, ctx)
            merge = await ReportFromId(merger, ctx)
            track_google_analytics_event("Duplicate", f"{dupe.report_id}", f"{ctx.author.id}")
            track_google_analytics_event("Merge", f"{merge.report_id}", f"{ctx.author.id}")

            if dupe is not None and merge is not None:
                for x in dupe.attachments:
                    await merge.add_attachment(ctx, ctx.interaction.guild.id, x, False)

                await dupe.resolve(ctx, ctx.interaction.guild.id, f"Merged into {merge.report_id}")
                await dupe.commit()

                await merge.addnote(602779023151595546, f"Merged `{dupe.report_id}` into `{merge.report_id}`", ctx,
                                    ctx.interaction.guild.id, True)
                await merge.commit()
                await merge.update(ctx, ctx.interaction.guild.id)
                await ctx.respond(f"Merged `{dupe.report_id}` into `{merge.report_id}`")
            else:
                await ctx.respond(f"Either the dupe, or the merged report was not found.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")


def setup(bot):
    log.info("[Report] ManagerCommands...")
    bot.add_cog(ManagerCommands(bot))
