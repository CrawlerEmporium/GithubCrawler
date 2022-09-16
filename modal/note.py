from discord import InputTextStyle, Interaction
from discord.ui import Modal, InputText

from crawler_utilities.utils.embeds import EmbedWithAuthorWithoutContext
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

        self.add_item(InputText(label="The note you want to add.", placeholder="What's the note you want to add?", required=True, style=InputTextStyle.long))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        description = self.children[0].value if self.children[0].value is not None else ""

        requestChannel = await self.bot.fetch_channel(self.channel)

        embed = EmbedWithAuthorWithoutContext(self.author)
        embed.title = f"New note for: {self.ticket.ticket_id} - {self.ticket.title}"
        embed.description = f"{description}** **"
        embed.set_footer(text=f"Added by {self.author.name}")

        if requestChannel is not None:
            await requestChannel.send(embed=embed)

        await self.ticket.addnote(self.author.id, description, self.ctx, self.interaction.guild_id)

        await finish_note_creation(self, interaction, embed)
