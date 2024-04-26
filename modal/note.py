from discord import InputTextStyle, Interaction, DiscordException
from discord.ui import Modal, InputText

from crawler_utilities.utils.embeds import EmbedWithRandomColor
from utils.ticketglobals import finish_note_creation


class Note(Modal):
    def __init__(self, ctx, ticket, author, channel) -> None:
        super().__init__(title=f"{ticket.ticket_id}: New Note")

        self.ctx = ctx
        self.bot = ctx.bot
        self.interaction = ctx.interaction
        self.ticket = ticket
        self.author = author
        self.channel = channel

        self.add_item(
            InputText(label="The note you want to add.", placeholder="What's the note you want to add?", required=True,
                      style=InputTextStyle.long))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        description = self.children[0].value if self.children[0].value is not None else ""

        requestChannel = None
        if self.channel is not None:
            # Custom code for Tools server, can be deleted if you don't need it.
            if (self.channel == 470673367628906496 or
                    self.channel == 647162018956181519 or
                    self.channel == 586998165962490023 or
                    self.channel == 607182631381237771):
                self.channel = 1007247989003272253
            requestChannel = await self.bot.fetch_channel(self.channel)

        embed = EmbedWithRandomColor()
        embed.title = f"New note for: {self.ticket.ticket_id} - {self.ticket.title}"
        embed.description = f"{description}** **"
        embed.set_footer(text=f"Added by {self.author.name}")

        await self.ticket.addnote(self.author.id, description, self.ctx, self.interaction.guild_id)

        await finish_note_creation(self, interaction, embed)

        try:
            if requestChannel is not None:
                await requestChannel.send(embed=embed)
        except DiscordException:
            pass
