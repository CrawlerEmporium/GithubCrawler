import csv
import io
from typing import Union

import discord
from discord import Option, SlashCommandGroup
from discord.abc import GuildChannel
from discord.ext import commands

import utils.globals as GG
from models.server import Server, Listen
from utils.autocomplete import get_server_identifiers, get_server_identifiers_no_alias
from utils.checks import is_manager
from utils.functions import loadGithubServers
# from utils.id_repair import apply_plan, build_plan, describe, fingerprint
from models.ticket import PRIORITY
from utils.ticketglobals import identifier_does_not_exist
from crawler_utilities.utils.confirmation import BotConfirmation
from crawler_utilities.utils.pagination import createPaginator

log = GG.log

TYPES = ['bug', 'feature', 'support']
RESOLVED = '\u2705'
OPEN = '\U0001F4EC'


async def find_in_tickets(db, identifier, searchTerm):
    results = []
    list = await db.find({"$text": {"$search": f"\"{searchTerm}\"", "$caseSensitive": False}}).to_list(length=None)
    for x in list:
        if identifier.upper() in x['ticket_id']:
            results.append(x)
    return results


class Issue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    issue = SlashCommandGroup("issue", "All commands that have effect on the issue tracker", checks=[commands.guild_only().predicate])

    # @issue.command(name="repair-ids")
    # async def repair_ids(self, ctx, approval: Option(str, "Preview token to apply the proposed changes", required=False, default=None)):
    #     """Preview or repair this server's rounded guild and channel IDs."""
    #     if ctx.author.id not in (ctx.guild.owner_id, GG.OWNER):
    #         return await ctx.respond("Only the server or bot owner can repair IDs.", ephemeral=True)
    #     await ctx.defer(ephemeral=True)
    #     try:
    #         channels = await ctx.guild.fetch_channels()
    #         plan, warnings = await build_plan(GG.MDB, ctx.guild, [g.id for g in self.bot.guilds] + [ctx.guild.id], channels)
    #     except (discord.HTTPException, ValueError) as error:
    #         return await ctx.respond(f"Could not create a repair plan: {error}", ephemeral=True)
    #
    #     token = fingerprint(plan, warnings)
    #     if approval is None:
    #         report = describe(plan, warnings)
    #         file = discord.File(io.BytesIO(report.encode('utf-8')), filename='id-repair-preview.txt')
    #         return await ctx.respond(
    #             f"Preview: {len(plan)} documents to change, {len(warnings)} unresolved items. "
    #             f"Rounded matches are suggestions, not proof: review the file and back up MongoDB first. "
    #             f"To apply this exact plan, run `/issue repair-ids approval:{token}`.",
    #             file=file, ephemeral=True)
    #     if approval != token:
    #         return await ctx.respond("The approval token does not match the current plan. Preview again; nothing was changed.", ephemeral=True)
    #     if not plan:
    #         return await ctx.respond("No changes to apply.", ephemeral=True)
    #     try:
    #         count = await apply_plan(GG.MDB, plan)
    #     except Exception as error:
    #         log.exception("ID repair failed; some documents may already have been updated")
    #         outcome = f"Repair stopped: {error}. Some documents may have changed; preview again."
    #     else:
    #         outcome = f"Updated {count} documents. {len(warnings)} unresolved items were left unchanged."
    #     try:
    #         await loadGithubServers()
    #         await GG.cache_identifiers()
    #         await GG.cache_server_channels()
    #         self.bot.prefixes.clear()
    #     except Exception:
    #         log.exception("Could not refresh caches after ID repair")
    #         outcome += " Cache refresh failed; restart the bot."
    #     await ctx.respond(outcome, ephemeral=True)

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
            await ctx.respond(
                "Server was successfully enabled.\nUse `\\issue new` to add a new listener to your server.")
        else:
            await ctx.respond("Server was already enabled.")

    # @issue.command(name="repair-server-id")
    # async def repair_server_id(self, ctx, old_server_id: Option(str, "The incorrect server ID currently stored in the database")):
    #     """Replace an incorrect stored guild ID with this guild's actual ID."""
    #     # if ctx.author.id != ctx.guild.owner_id:
    #     #     return await ctx.respond("Only the server owner can run this repair.", ephemeral=True)
    #
    #     try:
    #         old_id = int(old_server_id)
    #     except (TypeError, ValueError):
    #         return await ctx.respond("The old server ID must be a numeric Discord ID.", ephemeral=True)
    #
    #     new_id = ctx.guild.id
    #     if old_id == new_id:
    #         return await ctx.respond("The stored ID already matches this server.", ephemeral=True)
    #
    #     id_values = [old_id, str(old_id)]
    #     source = await GG.MDB.Github.find_one({"server": {"$in": id_values}})
    #     if source is None:
    #         return await ctx.respond("No server configuration was found for that old ID; nothing was changed.", ephemeral=True)
    #
    #     destination = await GG.MDB.Github.find_one({"server": {"$in": [new_id, str(new_id)]}})
    #     if destination is not None:
    #         return await ctx.respond("A server configuration already exists for this guild ID; nothing was changed.", ephemeral=True)
    #
    #     # Update dependent records before the primary document so a failed run can be retried.
    #     updates = (
    #         (GG.MDB.Managers, "server", new_id),
    #         (GG.MDB.TicketNums, "server", new_id),
    #         (GG.MDB.questions, "server", new_id),
    #         (GG.MDB.Tickets, "server_id", new_id),
    #         (GG.MDB.prefixes, "guild_id", str(new_id)),
    #     )
    #     migrated = {}
    #     for collection, field, replacement in updates:
    #         result = await collection.update_many(
    #             {field: {"$in": id_values}},
    #             {"$set": {field: replacement}},
    #         )
    #         migrated[collection.name] = result.modified_count
    #
    #     await GG.MDB.Github.update_one({"_id": source["_id"]}, {"$set": {"server": new_id}})
    #     await GG.cache_identifiers()
    #     await GG.cache_server_channels()
    #     await loadGithubServers()
    #
    #     details = ", ".join(f"{name}: {count}" for name, count in migrated.items())
    #     await ctx.respond(f"Updated the stored server ID to `{new_id}`. Related records updated — {details}.", ephemeral=True)

    @issue.command(name='new')
    @discord.default_permissions(
        administrator=True,
    )
    async def new(self,
                  ctx,
                  type: Option(str, description="What type of listener do you want?", choices=TYPES, required=True),
                  identifier: Option(str, description="Which identifier would you like it to have?", min_length=3,
                                     max_length=6, required=True),
                  tracker: Option(GuildChannel,
                                  description="The channel you want your voting/overview to be posted in",
                                  required=False, default=None),
                  channel: Option(GuildChannel,
                                  description="The channel you want your tickets to be posted in", required=False,
                                  default=None)):
        """
        Adds a new listener/tracker to the bot.
        """
        await ctx.defer()
        # CHECK IDENTIFIER
        identifier = identifier.upper()
        exist = await GG.MDB.TicketNums.find_one({"key": identifier, "server": ctx.guild.id})
        if exist is not None:
            if exist['server'] != ctx.guild.id:
                return await ctx.respond("This identifier is already in use, please select another one.")

        # CREATE CHANNELS
        if channel is None:
            channel = await ctx.guild.create_text_channel(f"{identifier}-listener")

        if tracker is None:
            tracker = await ctx.guild.create_text_channel(f"{identifier}-tracker")

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
            await GG.MDB.TicketNums.insert_one({"key": identifier, "server": ctx.guild.id, "amount": 0})
            await loadGithubServers()
            await GG.cache_identifiers()
            await GG.cache_server_channels()

        else:
            return await ctx.respond("The given channel or tracker ID's are invalid.")

        await ctx.respond(
            f"Created (or added) {channel.mention} as Posting Channel\nCreated (or added) {tracker.mention} as Tracking Channel.\n"
            f"It is using {identifier} as it's Identifier.\nIt is of the {type.capitalize()} type")

    @issue.command(name='trackers')
    async def trackers(self, ctx):
        """
        List all the currently enabled trackers for this server.
        """
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        server = Server.from_data(server)
        channels = "This server has the following channels setup:\n\n"
        for listen in server.listen:
            channels += f"Ticketing Channel: {self.bot.get_channel(listen.channel).mention}\n" \
                        f"Voting/Overview Channel: {self.bot.get_channel(listen.tracker).mention}\n" \
                        f"Using Identifier: ``{listen.identifier}``\n" \
                        f"Type: ``{listen.type}``\n\n"
        await ctx.respond(channels)

    @issue.command(name='remove')
    @discord.default_permissions(
        administrator=True,
    )
    async def remove(self, ctx, identifier: Option(str, "Which identifier would you like to delete?", autocomplete=get_server_identifiers_no_alias)):
        """Deletes an identifier"""
        await ctx.defer()
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        check = await GG.MDB.TicketNums.find_one({"key": identifier.upper(), "server": ctx.guild.id})

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
                await GG.MDB.TicketNums.delete_one({"key": identifier.upper(), "server": ctx.guild.id})
                await loadGithubServers()
                await GG.cache_identifiers()
                await GG.cache_server_channels()
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
    async def search(self, ctx,
                     identifier: Option(str, "In which identifier would you like to search?", autocomplete=get_server_identifiers),
                     keywords: Option(str, "What do you want to search?")):
        """Searches in all open tickets for a specified identifier"""
        await self.search_in_tickets(ctx, identifier, keywords)

    @issue.command(name='searchall')
    async def searchall(self, ctx,
                        identifier: Option(str, "In which identifier would you like to search?", autocomplete=get_server_identifiers),
                        keywords: Option(str, "What do you want to search?")):
        """Searches in all tickets for a specified identifier"""
        await self.search_in_tickets(ctx, identifier, keywords, False)

    @staticmethod
    async def search_in_tickets(ctx, identifier, keywords, open=True):
        await ctx.defer(ephemeral=True)
        allTickets = await find_in_tickets(GG.MDB.Tickets, identifier, keywords)
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for x in server['listen']:
            trackers.append(x['tracker'])
        results = []
        for ticket in allTickets:
            if open:
                if ticket['trackerId'] in trackers and ticket['severity'] != -1:
                    results.append(ticket)
            else:
                if ticket['trackerId'] in trackers:
                    results.append(ticket)
        if len(results) > 0:
            results = [(f"{r['ticket_id']} - {r['title']}", r) for r in results]
            paginator = createPaginator(ctx, results, title=f"Delete Commands for {ctx.interaction.guild}", author=True)
            await paginator.respond(ctx.interaction)
        else:
            await ctx.respond("No results found, please try with a different keyword.", ephemeral=True)

    @issue.command(name='open')
    async def issueOpen(self, ctx, identifier: Option(str, "Which identifier would you like to return?", autocomplete=get_server_identifiers)):
        """Lists all open tickets of a specified identifier and returns a csv file"""
        if not await is_manager(ctx):
            return await ctx.respond("You do not have the required permissions to use this command.", ephemeral=True)
        else:
            server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
            trackingChannels = []
            for x in server['listen']:
                trackingChannels.append(x['tracker'])
            query = {"ticket_id": {"$regex": f"{identifier}"}, "trackerId": {"$in": trackingChannels},
                     "severity": {"$ne": -1}}
            tickets = await GG.MDB.Tickets.find(query,
                                                {"_id": 0, "reporter": 0, "message": 0, "subscribers": 0,
                                                 "jumpUrl": 0,
                                                 "attachments": 0, "github_issue": 0, "github_repo": 0,
                                                 "trackerId": 0,
                                                 "milestone": 0}).to_list(length=None)
            if len(tickets) > 0:
                f = io.StringIO()

                csv.writer(f).writerow(
                    ["ticket_id", "title", "severity", "verification", "upvotes", "downvotes", "shrugs", "is_bug", "is_support",
                     "assigned"])
                for row in tickets:
                    assigned = row.get('assignee', False)
                    if assigned is not False:
                        assigned = True
                    csv.writer(f).writerow(
                        [row["ticket_id"], row["title"], PRIORITY.get(row["severity"], "Unknown"),
                         row["verification"],
                         row["upvotes"], row["downvotes"], row["shrugs"], row["is_bug"], row["is_support"], assigned])
                f.seek(0)

                buffer = io.BytesIO()
                buffer.write(f.getvalue().encode())
                buffer.seek(0)

                file = discord.File(buffer, filename=f"Open tickets for {identifier}.csv")
                await ctx.respond(file=file)
            else:
                await ctx.respond(f"No (open) tickets found with the {identifier} identifier.")

    @issue.command(name="alias")
    async def alias(self,
                    ctx,
                    identifier: Option(str, "For which identifier do you want to change the alias?",
                                       autocomplete=get_server_identifiers),
                    alias: Option(str, "What alias do you want to give the identifier?")):
        """Adds an alias for your identifier, for specification what an identifier does."""
        if not await is_manager(ctx):
            return await ctx.respond("You do not have the required permissions to use this command.", ephemeral=True)
        else:
            listen = None
            server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})

            for iden in server['listen']:
                if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                    iden['alias'] = alias
                    await GG.MDB.Github.replace_one({"server": ctx.interaction.guild_id}, server)
                    return await ctx.respond(f"Set alias ``{alias}`` for ``{identifier}``")

            if listen is None:
                return await identifier_does_not_exist(ctx, identifier)


def setup(bot):
    log.info("[Cogs] Issue...")
    bot.add_cog(Issue(bot))
