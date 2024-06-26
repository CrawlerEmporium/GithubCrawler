import discord
from discord import InputTextStyle, Interaction, ChannelType
from discord.ui import Modal, InputText

from crawler_utilities.cogs.stats import track_analytics_event
from crawler_utilities.utils.embeds import EmbedWithRandomColor
from crawler_utilities.utils.functions import splitDiscordEmbedField
from models.attachment import Attachment
from models.questions import Questionaire
from models.ticket import Ticket, get_next_ticket_num, TicketException
from utils.ticketglobals import finish_ticket_creation


class Feature(Modal):
    def __init__(self, identifier, bot, interaction, author, repo, tracker, channel,
                 custom_questions: Questionaire = None) -> None:
        super().__init__(title=f"{identifier}: Feature Request")

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
                self.add_item(InputText(label=question['text'], placeholder=question['placeholder'],
                                        style=InputTextStyle(question['style']), required=question['required'],
                                        row=question['position']))
        else:
            self.add_item(
                InputText(label="Title of the request", placeholder="Be as precise as possible.", required=True))
            self.add_item(
                InputText(label="Information", placeholder="Expand on your request, and be as detailed as possible.",
                          required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Who would use it?", required=False, style=InputTextStyle.long))
            self.add_item(InputText(label="How would it work?", required=False, style=InputTextStyle.long))
            self.add_item(
                InputText(label="Why should this be added?", placeholder="Justify why you think it'd help others.",
                          required=False, style=InputTextStyle.long))

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
            information = self.children[1].value
            who = self.children[2].value
            how = self.children[3].value
            why = self.children[4].value
            if information is not None and information != "":
                await splitDiscordEmbedField(embed, information, "Information")
                request += f"Information\n{information}\n\n"
            if who is not None and who != "":
                await splitDiscordEmbedField(embed, who, "Who would use it?")
                request += f"Who would use it?\n{who}\n\n"
            if how is not None and how != "":
                await splitDiscordEmbedField(embed, how, "How would it work?")
                request += f"How would it work?\n{how}\n\n"
            if why is not None and why != "":
                await splitDiscordEmbedField(embed, why, "Why should this be added?")
                request += f"Why should this be added?\n{why}\n\n"
        else:
            for index in range(1, len(self.children)):
                for index_child in self.children:
                    if index_child.row == index:
                        child = index_child
                if child.value is not None and child.value != "":
                    question = [x for x in self.custom_questions.questions if x['position'] == index][0]
                    label = question['text']
                    await splitDiscordEmbedField(embed, child.value, label)
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
            maxThreadTitleLength = 90 - extra
            if len(self.children[0].value) > maxThreadTitleLength:
                threadTitle = title if title is not None else f"{self.children[0].value[:maxThreadTitleLength]}..."
            else:
                threadTitle = title if title is not None else self.children[0].value
            thread = await requestChannel.create_thread(name=f"{self.ticket_id} - {threadTitle}", embed=embed, content=f"<@{self.author.id}>")
            thread
            jumpUrl = thread.jump_url

        ticket = await Ticket.new(self.author.id, self.ticket_id,
                                  title if title is not None else self.children[0].value,
                                  [Attachment(self.author.id, request)], is_bug=False,
                                  repo=self.repo, jumpUrl=jumpUrl, trackerId=self.tracker, thread=thread.id if thread is not None else None, server_id=interaction.guild_id)

        ticketMessage = await ticket.setup_message(self.bot, self.interaction.guild_id, ticket.trackerId)

        if thread is not None:
            await finish_ticket_creation(self, interaction, ticket, ticketMessage, requestChannel, False, False, thread)
            await thread.send(f"The ticket for this feature request can be found here: {ticketMessage.jump_url}")
        else:
            await finish_ticket_creation(self, interaction, ticket, ticketMessage, requestChannel, False, False)
