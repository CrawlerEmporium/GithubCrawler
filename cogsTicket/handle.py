from discord import Interaction
from discord.ext import commands

from crawler_utilities.cogs.stats import track_google_analytics_event
from modal.note import Note
from models.ticket import Ticket, TicketException
from utils.checks import is_manager_assignee_or_creator

from utils import globals as GG
log = GG.log


class HandleTicket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == 1:  # application_command (slash/context menus)
            return

        custom_id = interaction.data.get('custom_id', None)
        if custom_id is None or interaction.message is None:
            return

        components = interaction.message.components
        label = None
        for component in components:
            if hasattr(component, 'children'):
                for button in component.children:
                    if hasattr(button, 'custom_id'):
                        if button.custom_id == custom_id:
                            label = button.label
                            break

        message = interaction.message
        member = interaction.user
        server = interaction.guild

        if label not in (GG.UPVOTE, GG.DOWNVOTE, GG.INFORMATION, GG.SHRUG, GG.SUBSCRIBE, GG.RESOLVE, GG.NOTE) or member.bot or label is None:
            return

        try:
            ticket = await Ticket.from_message_id(message.id)
        except TicketException:
            return

        if label == GG.INFORMATION:
            track_google_analytics_event("Information", f"{ticket.ticket_id}", f"{member.id}")

        if ticket.is_bug or ticket.is_support:
            await self.handle_bug_or_support(self.bot, interaction, label, member, ticket, server)
        else:
            if server.owner_id == member.id:
                await self.handle_feature_server_owner(self.bot, interaction, label, member, ticket, server)
            else:
                await self.handle_feature_user(self.bot, interaction, label, member, message, ticket, server)

        await ticket.commit()
        await ticket.update(GG.ContextProxy(self.bot, interaction=interaction), server.id)

    @staticmethod
    async def handle_feature_user(bot, interaction, label, member, message, ticket, server):
        try:
            if label == GG.UPVOTE:
                print(f"Upvote: {member} - {ticket.ticket_id}")
                await ticket.upvote(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have upvoted {ticket.ticket_id}", ephemeral=True)
            elif label == GG.INFORMATION:
                print(f"Information: {member} - {ticket.ticket_id}")
                em = await ticket.get_embed(True)
                await interaction.response.send_message(embed=em, ephemeral=True)
            elif label == GG.SHRUG:
                print(f"Shrugged: {member} - {ticket.ticket_id}")
                await ticket.indifferent(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have shown indifference for {ticket.ticket_id}", ephemeral=True)
            elif label == GG.SUBSCRIBE:
                await HandleTicket.subscribe(interaction, member, ticket)
            elif label == GG.RESOLVE:
                await HandleTicket.resolve(bot, interaction, member, ticket, server)
            elif label == GG.NOTE:
                await HandleTicket.note(bot, interaction, ticket)
            else:
                print(f"Downvote: {member} - {ticket.ticket_id}")
                await ticket.downvote(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have downvoted {ticket.ticket_id}", ephemeral=True)
        except TicketException as e:
            if interaction.channel == message.channel:
                await interaction.response.send_message(content=str(e), ephemeral=True)
            else:
                await member.send(str(e))
                await interaction.response.defer()

    @staticmethod
    async def handle_feature_server_owner(bot, interaction, label, member, ticket, server):
        if label == GG.UPVOTE:
            print(f"Upvote: {member} - {ticket.ticket_id}")
            await ticket.force_accept(GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have accepted {ticket.ticket_id}", ephemeral=True)
        elif label == GG.INFORMATION:
            print(f"Information: {member} - {ticket.ticket_id}")
            em = await ticket.get_embed(True)
            await interaction.response.send_message(embed=em, ephemeral=True)
        elif label == GG.SHRUG:
            print(f"Shrugged: {member} - {ticket.ticket_id}")
            await ticket.indifferent(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have shown indifference for {ticket.ticket_id}", ephemeral=True)
        elif label == GG.SUBSCRIBE:
            await HandleTicket.subscribe(interaction, member, ticket)
        elif label == GG.RESOLVE:
            await ticket.resolve(GG.ContextProxy(bot, interaction=interaction, message=GG.FakeAuthor(member)), server.id, "Ticket closed.")
            await interaction.response.send_message(content=f"You have resolved {ticket.ticket_id}", ephemeral=True)
            await ticket.commit()
        elif label == GG.NOTE:
            await HandleTicket.note(bot, interaction, ticket)
        else:
            await ticket.force_deny(GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have denied {ticket.ticket_id}", ephemeral=True)
            await ticket.commit()

    @staticmethod
    async def handle_bug_or_support(bot, interaction, label, member, ticket, server):
        if label == GG.INFORMATION:
            print(f"Information: {member} - {ticket.ticket_id}")
            em = await ticket.get_embed(True)
            await interaction.response.send_message(embed=em, ephemeral=True)
        elif label == GG.SUBSCRIBE:
            await HandleTicket.subscribe(interaction, member, ticket)
        elif label == GG.RESOLVE:
            await HandleTicket.resolve(bot, interaction, member, ticket, server)
        elif label == GG.NOTE:
            await HandleTicket.note(bot, interaction, ticket)

    @staticmethod
    async def resolve(bot, interaction, member, ticket, server):
        if await is_manager_assignee_or_creator(member.id, server.id, ticket, bot):
            await ticket.resolve(GG.ContextProxy(bot, interaction=interaction, message=GG.FakeAuthor(member)), server.id, "Ticket closed.")
            await ticket.commit()
        else:
            await interaction.response.send_message(content=f"You do not have permissions to resolve/close this.", ephemeral=True)

    @staticmethod
    async def subscribe(interaction, member, ticket):
        if member.id in ticket.subscribers:
            ticket.unsubscribe(member.id)
            await interaction.response.send_message(content=f"You have unsubscribed from {ticket.ticket_id}", ephemeral=True)
        else:
            ticket.subscribe(member.id)
            await interaction.response.send_message(content=f"You have subscribed to {ticket.ticket_id}", ephemeral=True)

    @staticmethod
    async def note(bot, interaction, ticket):
        jumpUrl = ticket.jumpUrl.replace('https://discord.com/channels/','').split('/')
        channel = jumpUrl[1]
        author = interaction.user
        modal = Note(GG.ContextProxy(bot, interaction=interaction), ticket, author, channel)
        await interaction.response.send_modal(modal)


def setup(bot):
    log.info("[Ticket] HandleTicket...")
    bot.add_cog(HandleTicket(bot))
