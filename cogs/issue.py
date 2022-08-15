import csv
import io

import discord
from discord import Option, SlashCommandGroup, SlashCommandOptionType
from discord.ext import commands

import utils.globals as GG
from models.server import Server, Listen
from utils.autocomplete import get_server_identifiers
from utils.checks import isManager
from utils.functions import loadGithubServers, get_selection
from models.reports import Report, PRIORITY
from utils.reportglobals import IdentifierDoesNotExist
from crawler_utilities.utils.confirmation import BotConfirmation

log = GG.log

TYPES = ['bug', 'feature']


async def findInReports(db, identifier, searchTerm):
    results = []
    list = await db.find({"$text": {"$search": f"\"{searchTerm}\"", "$caseSensitive": False}}).to_list(length=None)
    for x in list:
        if identifier.upper() in x['report_id']:
            results.append(x)
    return results


class Issue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    issue = SlashCommandGroup("issue", "All commands that have effect on the issue tracker", checks=[commands.guild_only().predicate])

    @issue.command(name="enable")
    @discord.default_permissions(
        administrator=True,
    )
    async def enable(self, ctx):
        """
        Enables the features of IssueCrawler for this server.
        """
        guild = ctx.interaction.guild
        server = guild.id
        admin = guild.owner_id
        name = guild.name
        exist = await GG.MDB.Github.find_one({"server": server})
        if exist is None:
            gh = Server(name, server, admin)
            await GG.MDB.Github.insert_one(gh.to_dict())
            await loadGithubServers()
            await ctx.respond("Server was successfully enabled.\nUse `\\issue new` to add a new listener to your server.")
        else:
            await ctx.respond("Server was already enabled.")

    @issue.command(name='new')
    @discord.default_permissions(
        administrator=True,
    )
    async def new(self,
                  ctx,
                  type: Option(str, description="What type of listener do you want?", choices=TYPES, required=True),
                  identifier: Option(str, description="Which identifier would you it to have?", min_length=3, max_length=6, required=True),
                  tracker: Option(SlashCommandOptionType.channel, description="The channel you want your voting/overview to be posted in", required=False, default=None),
                  channel: Option(SlashCommandOptionType.channel, description="The channel you want your bugs/features to be posted in", required=False, default=None)):
        """
        Adds a new listener/tracker to the bot.
        """
        await ctx.defer()
        # CHECK IDENTIFIER
        identifier = identifier.upper()
        exist = await GG.MDB.ReportNums.find_one({"key": identifier, "server": ctx.guild.id})
        if exist is not None:
            if exist['server'] != ctx.guild.id:
                return await ctx.respond(
                    "This identifier is already in use, please select another one.")
        await GG.MDB.ReportNums.insert_one({"key": identifier, "server": ctx.guild.id, "amount": 0})

        # CREATE CHANNELS
        if channel is None:
            channel = await ctx.guild.create_text_channel(f"{identifier}-listener")
        else:
            channel = self.bot.get_channel(channel)

        if tracker is None:
            tracker = await ctx.guild.create_text_channel(f"{identifier}-tracker")
        else:
            tracker = self.bot.get_channel(tracker)

        # ADD LISTENER TO THE SERVER
        if channel is not None and tracker is not None:
            listener = Listen(channel=channel.id, tracker=tracker.id, identifier=identifier, type=type)
            data = await GG.MDB.Github.find_one({"server": ctx.guild.id})
            server = Server.from_data(data)
            listener = listener.to_dict()
            server = server.to_dict()
            oldListen = []
            for x in server['listen']:
                oldListen.append(x.to_dict())
            server['listen'] = oldListen
            server['listen'].append(listener)
            await GG.MDB.Github.replace_one({"server": ctx.guild.id}, server)
            await loadGithubServers()
        else:
            return await ctx.respond("The given channel or tracker ID's are invalid.")

        await ctx.respond(
            f"Created (or added) {channel.mention} as Posting Channel\nCreated (or added) {tracker.mention} as Tracking Channel.\n"
            f"It is using {identifier} as it's Identifier.")

    @issue.command(name='trackers')
    async def issueTrackers(self, ctx):
        """
        List all the currently enabled trackers for this server.
        """
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        server = Server.from_data(server)
        channels = "This server has the following channels setup:\n\n"
        for listen in server.listen:
            channels += f"Listening to: {self.bot.get_channel(listen.channel).mention}\n" \
                        f"Posting to: {self.bot.get_channel(listen.tracker).mention}\n" \
                        f"Using Identifier: ``{listen.identifier}``\n\n"
        await ctx.respond(channels)

    @issue.command(name='remove')
    @discord.default_permissions(
        administrator=True,
    )
    async def issueRemove(self, ctx, identifier: Option(str, "Which identifier would you like to delete?", autocomplete=get_server_identifiers)):
        await ctx.defer()
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        check = await GG.MDB.ReportNums.find_one({"key": identifier.upper(), "server": ctx.guild.id})

        if check is not None:
            confirmation = BotConfirmation(ctx, 0x012345)
            await confirmation.confirm(
                f"You are going to permanently delete {identifier}, are you sure?",
                channel=ctx.channel)
            if confirmation.confirmed:
                await confirmation.update(f"Confirmed, deleting {identifier} ...", color=0x55ff55)
                ch = None
                tr = None
                oldListen = []
                for x in server['listen']:
                    if x['identifier'] != identifier.upper():
                        oldListen.append(x)
                    else:
                        ch = self.bot.get_channel(x['channel'])
                        tr = self.bot.get_channel(x['tracker'])
                server['listen'] = oldListen
                await GG.MDB.Github.replace_one({"server": ctx.guild.id}, server)
                await GG.MDB.ReportNums.delete_one({"key": identifier.upper(), "server": ctx.guild.id})
                await confirmation.quit()
                if ch is not None and tr is not None:
                    return await ctx.respond(
                        f"``{identifier}`` removed from the database.\n\nYou can now safely remove these channels:\nListener: {ch.mention}, Tracker: {tr.mention}.\n"
                        f"**WARNING**: Deleting these channels could cause the bot to malfunction if you still have other Identifiers linked to these channels. \n"
                        f"Be **VERY** careful before deleting these channels and triple-check before doing so...")
                elif ch is not None:
                    return await ctx.respond(
                        f"``{identifier}`` removed from the database.\nIt's connected listing channel was not found.")
                elif tr is not None:
                    return await ctx.respond(
                        f"``{identifier}`` removed from the database.\nIt's connected tracking channel was not found.")
                else:
                    return await ctx.respond(
                        f"``{identifier}`` removed from the database.\nIt's connected channels were not found.")
            else:
                await confirmation.quit()
                return await ctx.respond("Deletion was canceled", delete_after=5)
        else:
            await ctx.respond(f"``{identifier}`` not found...")

    @issue.command(name='search')
    @commands.guild_only()
    async def issueSearch(self, ctx, identifier, *, keywords):
        allReports = await findInReports(GG.MDB.Reports, identifier, keywords)
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for x in server['listen']:
            trackers.append(x['tracker'])
        results = []
        for report in allReports:
            if report['trackerId'] in trackers and report['severity'] != -1:
                results.append(report)
        if len(results) > 0:
            results = [(f"{r['report_id']} - {r['title']}", r) for r in results]
            selection = await get_selection(ctx, results, force_select=True)
            if selection is not None:
                report = await Report.from_id(selection['report_id'], ctx.guild.id)
                if report is not None:
                    await ctx.send(embed=await report.get_embed(True, ctx))
                else:
                    await ctx.send("Selected report not found.")
            else:
                return
        else:
            await ctx.send("No results found, please try with a different keyword.")

    @issue.command(name='searchAll')
    @commands.guild_only()
    async def issueSearchAll(self, ctx, identifier, *, keywords):
        allReports = await findInReports(GG.MDB.Reports, identifier, keywords)
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for x in server['listen']:
            trackers.append(x['tracker'])
        results = []
        for report in allReports:
            if report['trackerId'] in trackers:
                results.append(report)
        if len(results) > 0:
            results = [(f"{r['report_id']} - {r['title']}", r) for r in results]
            selection = await get_selection(ctx, results, force_select=True)
            if selection is not None:
                report = await Report.from_id(selection['report_id'], ctx.guild.id)
                if report is not None:
                    await ctx.send(embed=await report.get_embed(True, ctx))
                else:
                    await ctx.send("Selected report not found.")
            else:
                return
        else:
            await ctx.send("No results found, please try with a different keyword.")

    @issue.command(name='open')
    @commands.guild_only()
    async def issueOpen(self, ctx, identifier=None):
        if await isManager(ctx):
            if identifier is None:
                server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
                identString = ""
                for x in server['listen']:
                    identString += f"``{x['identifier']}``, "
                await ctx.send(
                    f"Please supply me with an identifier for this server.\nThis server has the following identifiers:\n{identString[:-2]}")
            else:
                server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
                trackingChannels = []
                for x in server['listen']:
                    trackingChannels.append(x['tracker'])
                query = {"report_id": {"$regex": f"{identifier}"}, "trackerId": {"$in": trackingChannels},
                         "severity": {"$ne": -1}}
                reports = await GG.MDB.Reports.find(query,
                                                    {"_id": 0, "reporter": 0, "message": 0, "subscribers": 0, "jumpUrl": 0,
                                                     "attachments": 0, "github_issue": 0, "github_repo": 0, "trackerId": 0,
                                                     "milestone": 0}).to_list(length=None)
                if len(reports) > 0:
                    f = io.StringIO()

                    csv.writer(f).writerow(
                        ["report_id", "title", "severity", "verification", "upvotes", "downvotes", "shrugs", "is_bug", "assigned"])
                    for row in reports:
                        assigned = row.get('assignee', False)
                        if assigned is not False:
                            assigned = True
                        csv.writer(f).writerow(
                            [row["report_id"], row["title"], PRIORITY.get(row["severity"], "Unknown"), row["verification"],
                             row["upvotes"], row["downvotes"], row["shrugs"], row["is_bug"], assigned])
                    f.seek(0)

                    buffer = io.BytesIO()
                    buffer.write(f.getvalue().encode())
                    buffer.seek(0)

                    file = discord.File(buffer, filename=f"Open Reports for {identifier}.csv")
                    await ctx.send(file=file)
                else:
                    await ctx.send(f"No (open) reports found with the {identifier} identifier.")

    @issue.command(name="alias")
    async def aliasidentifier(self,
                              ctx,
                              identifier: Option(str, "For which identifier do you want to change the alias?", autocomplete=get_server_identifiers),
                              alias: Option(str, "What alias do you want to give the identifier?")):
        """Adds an alias for your identifier, for specification what an identifier does."""
        if await isManager(ctx):
            listen = None
            server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})

            for iden in server['listen']:
                if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                    iden['alias'] = alias
                    await GG.MDB.Github.replace_one({"server": ctx.interaction.guild_id}, server)
                    return await ctx.respond(f"Set alias ``{alias}`` for ``{identifier}``")

            if listen is None:
                return await IdentifierDoesNotExist(ctx, identifier)


def setup(bot):
    log.info("[Cogs] Issue...")
    bot.add_cog(Issue(bot))
