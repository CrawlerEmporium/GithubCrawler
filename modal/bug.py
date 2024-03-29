import discord
from discord import InputTextStyle, Interaction, ChannelType
from discord.ui import Modal, InputText

from crawler_utilities.utils.embeds import EmbedWithRandomColor
from models.attachment import Attachment
from models.questions import Questionaire
from models.ticket import Ticket, get_next_ticket_num, TicketException
import utils.globals as GG
from utils.ticketglobals import finish_ticket_creation


class Bug(Modal):
    def __init__(self, identifier, bot, interaction, author, repo, tracker, channel, custom_questions: Questionaire = None) -> None:
        super().__init__(title=f"{identifier}: Bug Ticket")

        self.bot = bot
        self.interaction = interaction
        self.author = author
        self.repo = repo
        self.tracker = tracker
        self.channel = channel
        self.custom_questions = custom_questions
        self.identifier = identifier
        self.ticket_id = None

        if custom_questions is not None:
            for question in custom_questions.questions:
                self.add_item(InputText(label=question['text'], placeholder=question['placeholder'], style=InputTextStyle(question['style']), required=question['required'], row=question['position']))
        else:
            self.add_item(InputText(label="What is the bug?", placeholder="A quick description of the bug.", required=True))
            self.add_item(InputText(label="Steps to reproduce", placeholder="How the bug occured, and how to reproduce it.", required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Severity", placeholder="Trivial / Low / Medium / High / Critical", required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Additional information", placeholder="Any additional information you want to give.", required=False, style=InputTextStyle.long))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        title = None
        thread = None
        for child in self.children:
            if child.row == 0:
                title = child.value
        request = ""

        requestChannel = self.bot.get_channel(self.channel)
        embed = EmbedWithRandomColor()
        embed.set_footer(text=f"Added by {self.author.name}")
        embed.title = title if title is not None else self.children[0].value
        if self.custom_questions is None:
            if self.children[1].value is not None and self.children[1].value != "":
                embed.add_field(name="Steps to reproduce", value=self.children[1].value, inline=False)
                request += f"Steps to reproduce\n{self.children[1].value}\n\n"
            if self.children[2].value is not None and self.children[2].value != "":
                embed.add_field(name="Severity", value=self.children[2].value, inline=False)
                request += f"Severity\n{self.children[2].value}\n\n"
            if self.children[3].value is not None and self.children[3].value != "":
                embed.add_field(name="Additional information", value=self.children[3].value, inline=False)
                request += f"Additional information\n{self.children[3].value}\n\n"
        else:
            for index in range(1, len(self.children)):
                for index_child in self.children:
                    if index_child.row == index:
                        child = index_child
                if child.value is not None and child.value != "":
                    question = [x for x in self.custom_questions.questions if x['position'] == index][0]
                    label = question['text']
                    embed.add_field(name=label, value=child.value, inline=False)
                    request += f"{label}\n{child.value}\n\n"

        if self.identifier is not None:
            try:
                ticket_num = await get_next_ticket_num(self.identifier, interaction.guild_id)
                self.ticket_id = f"{self.identifier}-{ticket_num}"
            except TicketException as e:
                return await interaction.response.send_message(e, ephemeral=True)

        if requestChannel.type != ChannelType.forum:
            message = await requestChannel.send(embed=embed)
            jumpUrl = message.jump_url
        else:
            extra = len(f"{self.ticket_id} - ")
            extra += len(f"[Resolved] ")
            maxThreadTitleLength = 97 - extra
            if len(self.children[0].value) > maxThreadTitleLength:
                threadTitle = title if title is not None else f"{self.children[0].value[:maxThreadTitleLength]}..."
            else:
                threadTitle = title if title is not None else self.children[0].value
            thread = await requestChannel.create_thread(name=f"{self.ticket_id} - {threadTitle}", embed=embed, content=f"<@{self.author.id}>")
            jumpUrl = thread.jump_url

        ticket = await Ticket.new(self.author.id, self.ticket_id, title if title is not None else self.children[0].value,
                                  [Attachment(self.author.id, request)], is_bug=True,
                                  repo=self.repo, jumpUrl=jumpUrl, trackerId=self.tracker, thread=thread.id if thread is not None else None, server_id=interaction.guild_id)

        if interaction.guild_id in GG.SERVERS:
            if self.repo is not None:
                await ticket.setup_github(self.bot, self.interaction.guild_id)

        ticketMessage = await ticket.setup_message(self.bot, self.interaction.guild_id, ticket.trackerId)

        if thread is not None:
            await finish_ticket_creation(self, interaction, ticket, ticketMessage, requestChannel, True, False, jumpUrl)
            await thread.send(f"The ticket for this bug report can be found here: {ticketMessage.jump_url}")
        else:
            await finish_ticket_creation(self, interaction, ticket, ticketMessage, requestChannel, True, False)
