import discord
from crawler_utilities.cogs.stats import track_google_analytics_event

import utils.globals as GG
from models.ticket import Ticket

TICKETS = []


def loop(result, error):
    if error:
        raise error
    elif result:
        TICKETS.append(result)


def get_all_tickets():
    collection = GG.MDB['Tickets']
    cursor = collection.find()
    TICKETS.clear()
    cursor.each(callback=loop)
    return TICKETS


async def finish_ticket_creation(self, interaction, ticket, ticketMessage, requestChannel, bug=False, support=False, forumPost=None):
    await ticket.commit()
    embed = await admission_successful_embed(self.ticket_id, self.author, bug, support, requestChannel, ticketMessage, forumPost)
    if self.author.dm_channel is not None:
        DM = self.author.dm_channel
    else:
        DM = await self.author.create_dm()
    try:
        await DM.send(embed=embed)
    except discord.Forbidden:
        pass
    await interaction.followup.send(
        f"Your submission ``{ticket.ticket_id}`` was accepted, please check your DM's for more information.\n"
        f"If no DM was received, you probably have it turned off, and you should check the tracker channel of the server the request was made in.",
        ephemeral=True)


async def finish_note_creation(self, interaction, embed):
    if self.author.dm_channel is not None:
        DM = self.author.dm_channel
    else:
        DM = await self.author.create_dm()
    try:
        await DM.send(embed=embed)
    except discord.Forbidden:
        pass
    await interaction.followup.send(
        f"Your note for ``{self.ticket.ticket_id}`` was added, please check your DM's for more information.\n"
        f"If no DM was received, you probably have it turned off, and you should check the tracker channel of the server the request was made in.",
        ephemeral=True)


async def admission_successful_embed(ticket_id, author, bug, support, requestChannel, ticketMessage, forumPost=None):
    embed = discord.Embed()
    embed.title = f"Your submission ``{ticket_id}`` was accepted."
    if bug:
        track_google_analytics_event("Bug report", f"{ticket_id}", f"{author.id}")
        embed.description = f"Your bug was successfully posted in <#{requestChannel.id}>!"
    elif support:
        track_google_analytics_event("Support Ticket", f"{ticket_id}", f"{author.id}")
        embed.description = f"Your support ticket was successfully posted in <#{requestChannel.id}>!"
    else:
        track_google_analytics_event("Feature Request", f"{ticket_id}", f"{author.id}")
        embed.description = f"Your feature request was successfully posted in <#{requestChannel.id}>!"
    embed.add_field(name="Status Checking", value=f"To check on its status: `/view {ticket_id}`.",
                    inline=False)
    embed.add_field(name="Note Adding",
                    value=f"To add a note: `/note {ticket_id} <comment>`.",
                    inline=False)
    embed.add_field(name="Subscribing",
                    value=f"To subscribe: `/subscribe {ticket_id}`. (This is only for others, the submitter is automatically subscribed).",
                    inline=False)
    if not bug:
        embed.add_field(name="Voting",
                        value=f"You can find the ticket here: [Click me]({ticketMessage.jump_url})",
                        inline=False)
    if forumPost is not None:
        embed.add_field(name="Discussion Post",
                        value=f"You can find the created forum post here: [Click me]({forumPost})",
                        inline=False)
    return embed


async def identifier_does_not_exist(ctx, identifier):
    return await ctx.respond(f"The identifier ``{identifier}`` could not be found.\n"
                             f"If the identifier was shown in the option box, please contact the developer of the bot through the ``support`` command.\n\n"
                             f"Otherwise this command can only be used on servers that have the feature request functionality of the bot enabled.",
                             ephemeral=True)


async def ticket_from_id(_id, ctx):
    ticket_id = _id.split(" | ")[0]
    guild_id = ctx.interaction.guild_id
    ticket = await Ticket.from_id(ticket_id, guild_id)
    return ticket
