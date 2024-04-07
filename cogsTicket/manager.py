import copy

import discord
from discord import slash_command, Option, permissions, ChannelType
from discord.ext import commands

from crawler_utilities.cogs.stats import track_analytics_event
from crawler_utilities.utils.pagination import BotEmbedPaginator
from models.ticket import Ticket, get_next_ticket_num
from utils.autocomplete import get_server_tickets, get_server_identifiers
from utils.checks import is_manager, is_manager_assignee_or_creator
from utils.ticketglobals import ticket_from_id, identifier_does_not_exist

from utils import globals as GG
log = GG.log


class ManagerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="resolve")
    @permissions.guild_only()
    async def resolve(self, ctx, _id: Option(str, "Which ticket do you want to resolve?", autocomplete=get_server_tickets), msg: Option(str, "Optional resolve comment", default="")):
        """Server Managers and Identifier Managers only - Resolves a ticket."""
        await ctx.defer()
        ticket = await ticket_from_id(_id, ctx)
        if await is_manager_assignee_or_creator(ctx.interaction.user.id, ctx.guild.id, ticket, ctx.bot):
            await ticket.resolve(ctx, ctx.guild.id, msg)
            await ticket.commit()
            await ctx.respond(f"Resolved `{ticket.ticket_id}`: {ticket.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="unresolve")
    @permissions.guild_only()
    async def unresolve(self, ctx, _id: Option(str, "Which ticket do you want to unresolve?", autocomplete=get_server_tickets), msg: Option(str, "Optional unresolve comment", default="")):
        """Server Managers and Identifier Managers only - Unresolves a ticket."""
        await ctx.defer()
        ticket = await ticket_from_id(_id, ctx)
        if await is_manager(ctx, ticket):
            await ticket.unresolve(ctx, ctx.guild.id, msg)
            await ticket.commit()
            await ctx.respond(f"Unresolved `{ticket.ticket_id}`: {ticket.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="reidentify")
    @permissions.guild_only()
    async def reidentify(self, ctx, _id: Option(str, "Which ticket do you want to reidentify?", autocomplete=get_server_tickets), identifier: Option(str, "To which identifier do you want to change this ticket?", autocomplete=get_server_identifiers)):
        """Server Managers only - Changes the identifier of a ticket."""
        await ctx.defer()
        if await is_manager(ctx):
            exists = False

            server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
            for iden in server['listen']:
                if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                    identifier = iden['identifier'].upper()
                    channel = iden['channel']
                    exists = True

            if not exists:
                return await identifier_does_not_exist(ctx, identifier)

            id_num = await get_next_ticket_num(identifier, ctx.interaction.guild.id)
            requestChannel = self.bot.get_channel(channel)

            ticket = await ticket_from_id(_id, ctx)
            new_ticket = copy.copy(ticket)
            await ticket.resolve(ctx, ctx.guild.id, f"Reassigned as `{identifier}-{id_num}`.", False)
            await ticket.commit()

            new_ticket.ticket_id = f"{identifier}-{id_num}"
            msg = await self.bot.get_channel(ticket.trackerId).send(embed=await new_ticket.get_embed())

            if requestChannel.type == ChannelType.forum:
                embed = await new_ticket.get_embed()
                thread = await requestChannel.create_thread(name=f"{new_ticket.ticket_id} - {new_ticket.title}", embed=embed, content=f"<@{new_ticket.reporter}>")
                new_ticket.jumpUrl = thread.jump_url
                new_ticket.thread = thread.id

            new_ticket.message = msg.id
            if new_ticket.github_issue:
                await new_ticket.update_labels()
                await new_ticket.edit_title(f"{new_ticket.ticket_id} {new_ticket.title}")
            await new_ticket.commit()
            await ctx.respond(f"Reassigned {ticket.ticket_id} as {new_ticket.ticket_id}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="rename")
    @permissions.guild_only()
    async def rename(self, ctx, _id: Option(str, "Which ticket do you want to rename?", autocomplete=get_server_tickets), name: Option(str, "The new title for the ticket")):
        """Server Managers and Identifier Managers only - Changes the title of a ticket."""
        await ctx.defer()
        ticket = await ticket_from_id(_id, ctx)
        if await is_manager(ctx, ticket):
            ticket.title = name
            if ticket.github_issue and ticket.repo is not None:
                await ticket.edit_title(f"{ticket.title}", f"{ticket.ticket_id} ")
            await ticket.commit()
            await ticket.update(ctx, ctx.interaction.guild.id)
            if ticket.thread:
                channel = await ctx.bot.fetch_channel(ticket.thread)
                await channel.edit(name=f"{ticket.ticket_id} - {name}")
                await channel.send(f"Renamed {ticket.ticket_id} as {ticket.title}.")
            await ctx.respond(f"Renamed {ticket.ticket_id} as {ticket.title}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="assign")
    @permissions.guild_only()
    async def assign(self, ctx, member: Option(discord.Member, "What user do you want to assign?"), _id: Option(str, "To which ticket do you want to assign the user?", autocomplete=get_server_tickets)):
        """Server Managers and Identifier Managers only - Assign a member to a ticket."""
        await ctx.defer()
        ticket = await ticket_from_id(_id, ctx)
        if await is_manager(ctx, ticket):

            await track_analytics_event("IssueCrawler", "Assign", f"{ticket.ticket_id}", f"{ctx.interaction.user.id}")

            ticket.assignee = member.id

            await ticket.addnote(ctx.interaction.user.id, f"Assigned {ticket.ticket_id} to {member.mention}", ctx, ctx.interaction.guild_id)
            await ticket.commit()
            await ticket.update(ctx, ctx.interaction.guild_id)
            await ctx.respond(f"Assigned {ticket.ticket_id} to {member.mention}")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="assigned")
    @permissions.guild_only()
    async def assigned(self, ctx, member: Option(discord.Member, "For which user?")):
        """Get a list of assigned tickets from a member. (or yourself)"""
        await ctx.respond("Gathering information...", delete_after=5)
        if ctx.interaction.user.id == member.id:
            await self.get_assigned_tickets(ctx, member)
        elif await is_manager(ctx):
            await self.get_assigned_tickets(ctx, member)
        else:
            return await ctx.respond("Only managers can request the assigned list for other people.")

    async def get_assigned_tickets(self, ctx, member):
        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild.id})
        trackers = []
        for listen in server['listen']:
            trackers.append(listen['tracker'])

        query = {"trackerId": {"$in": trackers}}
        tickets = await GG.MDB.Tickets.find(query).to_list(length=None)

        if len(tickets) == 0:
            return await ctx.respond(f"No tickets found.")

        assigned_tickets = []
        for ticket in tickets:
            if member.id == ticket.get('assignee', []) and ticket['severity'] != -1:
                rep = {
                    "ticket_id": ticket['ticket_id'],
                    "title": ticket['title']
                }
                assigned_tickets.append(rep)

        if len(assigned_tickets) > 0:
            embedList = []
            for i in range(0, len(assigned_tickets), 10):
                lst = assigned_tickets[i:i + 10]
                desc = ""
                for item in lst:
                    desc += f'• `{item["ticket_id"]}` - {item["title"]}\n'
                if isinstance(member, discord.Member) and member.color != discord.Colour.default():
                    embed = discord.Embed(description=desc, color=member.color)
                else:
                    embed = discord.Embed(description=desc)
                embed.set_author(name=f'Assigned open tickets for {member.nick if member.nick is not None else member.name}', icon_url=member.display_avatar.url)
                embedList.append(embed)

            paginator = BotEmbedPaginator(ctx, embedList)
            await paginator.run()
        else:
            return await ctx.respond(f"{member.mention} doesn't have any assigned tickets on this server.")

    @slash_command(name="unassign")
    @permissions.guild_only()
    async def unassign(self, ctx, _id: Option(str, "Unassign everyone from this ticket", autocomplete=get_server_tickets)):
        """Server Managers only - Unassign a member from a ticket."""
        await ctx.defer()
        ticket = await ticket_from_id(_id, ctx)
        if await is_manager(ctx, ticket):
            await track_analytics_event("IssueCrawler", "Unassign", f"{ticket.ticket_id}", f"{ctx.interaction.user.id}")

            ticket.assignee = None

            await ticket.addnote(ctx.interaction.user.id, f"Cleared assigned user from {ticket.ticket_id}", ctx, ctx.interaction.guild.id)
            await ticket.commit()
            await ticket.update(ctx, ctx.interaction.guild.id)
            await ctx.respond(f"Cleared assigned user of {ticket.ticket_id}.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")

    @slash_command(name="merge")
    @permissions.guild_only()
    async def merge(self, ctx, duplicate: Option(str, "Duped ticket", autocomplete=get_server_tickets), merger: Option(str, "Merge into this ticket", autocomplete=get_server_tickets)):
        """Server Managers only - Merges duplicate into mergeTo."""
        await ctx.defer()
        if await is_manager(ctx):
            dupe = await ticket_from_id(duplicate, ctx)
            merge = await ticket_from_id(merger, ctx)
            await track_analytics_event("IssueCrawler", "Duplicate", f"{dupe.ticket_id}", f"{ctx.author.id}")
            await track_analytics_event("IssueCrawler", "Merge", f"{merge.ticket_id}", f"{ctx.author.id}")

            if dupe is not None and merge is not None:
                for x in dupe.attachments:
                    await merge.add_attachment(ctx, ctx.interaction.guild.id, x, False)

                await dupe.resolve(ctx, ctx.interaction.guild.id, f"Merged into {merge.ticket_id}")
                await dupe.commit()

                await merge.addnote(602779023151595546, f"Merged `{dupe.ticket_id}` into `{merge.ticket_id}`", ctx,
                                    ctx.interaction.guild.id, True)
                await merge.commit()
                await merge.update(ctx, ctx.interaction.guild.id)
                await ctx.respond(f"Merged `{dupe.ticket_id}` into `{merge.ticket_id}`")
            else:
                await ctx.respond(f"Either the dupe, or the merged ticket was not found.")
        else:
            await ctx.respond("You do not have the appropriate permissions to use this command.")


def setup(bot):
    log.info("[Ticket] ManagerCommands...")
    bot.add_cog(ManagerCommands(bot))
