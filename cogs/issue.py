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
