import discord
from discord import slash_command, Option, permissions
from discord.ext import commands

from cogsTicket.handle import HandleTicket
from crawler_utilities.cogs.stats import track_analytics_event
from crawler_utilities.utils.embeds import EmbedWithRandomColor
from utils.autocomplete import get_server_tickets, get_server_feature_identifiers
from utils.ticketglobals import ticket_from_id, get_all_tickets

from utils import globals as GG
log = GG.log


class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="view")
    @permissions.guild_only()
    async def view(self, ctx, _id: Option(str, "Which ticket do you want to view?", autocomplete=get_server_tickets)):
        """Shows basic overview of requested ticket."""
        ticket = await ticket_from_id(_id, ctx)
        user = ctx.interaction.user
        await track_analytics_event("IssueCrawler", "Information", f"{ticket.ticket_id}", f"{user.id}")
        interaction = await ctx.respond(f"Loading ticket... Please hold...")
        message_id = (await interaction.original_response()).id
        message = await interaction.channel.fetch_message(message_id)
        await ticket.get_ticket_notes(ctx, message)

    @slash_command(name="upvote")
    @permissions.guild_only()
    async def upvote(self, ctx, _id: Option(str, "Which ticket do you want to upvote?", autocomplete=get_server_tickets), msg: Option(str, "Do you have any added comment for this upvote?", default="")):
        """Adds an upvote to the selected ticket."""
        ticket = await ticket_from_id(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await ticket.upvote(user.id, msg, ctx, guild_id)
        await ticket.commit()
        await ctx.respond(f"Added your upvote to `{ticket.ticket_id}` - {ticket.title}.", ephemeral=True)
        await track_analytics_event("IssueCrawler", "Upvote", f"{ticket.ticket_id}", f"{user.id}")
        await ticket.update(ctx, guild_id)

    @slash_command(name="downvote")
    @permissions.guild_only()
    async def downvote(self, ctx, _id: Option(str, "Which ticket do you want to downvote?", autocomplete=get_server_tickets), msg: Option(str, "Do you have any added comment for this downvote?", default="")):
        """Adds a downvote to the selected ticket."""
        ticket = await ticket_from_id(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await ticket.downvote(user.id, msg, ctx, guild_id)
        await ticket.commit()
        await ctx.respond(f"Added your downvote to `{ticket.ticket_id}` - {ticket.title}.", ephemeral=True)
        await track_analytics_event("IssueCrawler", "Downvote", f"{ticket.ticket_id}", f"{user.id}")
        await ticket.update(ctx, guild_id)

    @slash_command(name="indifferent")
    @permissions.guild_only()
    async def indifferent(self, ctx, _id: Option(str, "Which ticket do you want to be indifferent about?", autocomplete=get_server_tickets), msg: Option(str, "Do you have any added comment for the indifference?", default="")):
        """Adds an indifference to the selected ticket."""
        ticket = await ticket_from_id(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await ticket.indifferent(user.id, msg, ctx, guild_id)
        await ticket.commit()
        await ctx.respond(f"Added your indifference to `{ticket.ticket_id}` - {ticket.title}.", ephemeral=True)
        await track_analytics_event("IssueCrawler", "Indifference", f"{ticket.ticket_id}", f"{user.id}")
        await ticket.update(ctx, guild_id)

    @slash_command(name="note")
    @permissions.guild_only()
    async def note(self, ctx, _id: Option(str, "Which ticket do you want to add a note to?", autocomplete=get_server_tickets)):
        """Adds a note to a ticket."""
        ticket = await ticket_from_id(_id, ctx)
        await HandleTicket.note(ctx.bot, ctx.interaction, ticket)

    @slash_command(name="subscribe")
    @permissions.guild_only()
    async def subscribe(self, ctx, _id: Option(str, "Which ticket do you want to (un)subscribe to?", autocomplete=get_server_tickets)):
        """Subscribes (or unsubscribe) to a ticket."""
        ticket = await ticket_from_id(_id, ctx)
        user = ctx.interaction.user
        if user.id in ticket.subscribers:
            ticket.unsubscribe(user.id)
            await ctx.respond(f"Unsubscribed from `{ticket.ticket_id}` - {ticket.title}.", ephemeral=True)
            await track_analytics_event("IssueCrawler", "Unsubscribe", f"{ticket.ticket_id}", f"{user.id}")
        else:
            ticket.subscribe(user.id)
            await ctx.respond(f"Subscribed to `{ticket.ticket_id}` - {ticket.title}.", ephemeral=True)
            await track_analytics_event("IssueCrawler", "Subscribe", f"{ticket.ticket_id}", f"{user.id}")
        await ticket.commit()

    @slash_command(name="subscriptions")
    @permissions.guild_only()
    async def subscriptions(self, ctx):
        """Gets a list of all tickets you are subscribed to."""
        tickets = await GG.MDB['Tickets'].find({"severity": {"$ne": -1}}).to_list(length=None)

        user = ctx.interaction.user
        subscribed_tickets = []

        for ticket in tickets:
            if user.id in ticket.get('subscribers', []):
                rep = {
                    "ticket_id": ticket['ticket_id'],
                    "title": ticket['title'],
                    "jumpUrl": ticket.get('jumpUrl', "NoLink")
                }
                subscribed_tickets.append(rep)

        embed_queue = [EmbedWithRandomColor()]
        embed_queue[-1].title = f"Your subscribed tickets."

        for ticket in subscribed_tickets:
            jumpUrl = ticket.get("jumpUrl", "NoLink")
            if jumpUrl is not None and jumpUrl != "NoLink":
                msg_url = f"[Link]({jumpUrl})"
            else:
                msg_url = f"NoLink"
            if len(embed_queue[-1].fields) == 25 or len(embed_queue[-1]) > 5000:
                embed_queue.append(discord.Embed(colour=embed_queue[-1].colour, title=embed_queue[-1].title))
            embed_queue[-1].add_field(name=f"{ticket['ticket_id']}", value=f"{ticket['title']} - {msg_url}", inline=False)
        for embed in embed_queue:
            if ctx.interaction.user.dm_channel is not None:
                DM = ctx.interaction.user.dm_channel
            else:
                DM = await ctx.interaction.user.create_dm()
            try:
                await DM.send(embed=embed)
            except discord.Forbidden:
                pass
        await ctx.respond(
                f"Please check your DM's for your subscriptions.\n"
                f"If no DM was received, you probably have it turned off.",
                ephemeral=True)

    @slash_command(name="unsuball")
    @permissions.guild_only()
    async def unsuball(self, ctx):
        """Unsubscribes from all tickets."""
        tickets = get_all_tickets()
        num_unsubbed = 0
        collection = GG.MDB['Tickets']

        user = ctx.interaction.user

        for ticket in tickets:
            if user.id in ticket.get('subscribers', []):
                ticket['subscribers'].remove(user.id)
                num_unsubbed += 1
                await collection.replace_one({"ticket_id": ticket['ticket_id']}, ticket)

        await ctx.respond(f"Unsubscribed from {num_unsubbed} tickets.", ephemeral=True)


def setup(bot):
    log.info("[Ticket] TicketCommands...")
    bot.add_cog(TicketCommands(bot))
