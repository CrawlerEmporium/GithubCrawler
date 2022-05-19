import discord
from discord import InputTextStyle, Interaction
from discord.ui import Modal, InputText

from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.utils.embeds import EmbedWithAuthorWithoutContext
from models.attachment import Attachment
from models.questions import Questionaire
from models.reports import Report
from utils.reportglobals import finishReportCreation


class Feature(Modal):
    def __init__(self, identifier, bot, interaction, report_id, author, repo, tracker, channel, custom_questions: Questionaire = None) -> None:
        super().__init__(f"{identifier}: Feature Request")

        self.bot = bot
        self.interaction = interaction
        self.report_id = report_id
        self.author = author
        self.repo = repo
        self.tracker = tracker
        self.channel = channel
        self.custom_questions = custom_questions

        if custom_questions is not None:
            for question in custom_questions.questions:
                self.add_item(InputText(label=question['text'], placeholder=question['placeholder'], style=InputTextStyle(question['style']), required=question['required'], row=question['position']))
        else:
            self.add_item(InputText(label="Title of the request", placeholder="Be as precise as possible.", required=True))
            self.add_item(InputText(label="Information", placeholder="Expand on your request, and be as detailed as possible.", required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Who would use it?", required=False, style=InputTextStyle.long))
            self.add_item(InputText(label="How would it work?", required=False, style=InputTextStyle.long))
            self.add_item(InputText(label="Why should this be added?", placeholder="Justify why you think it'd help others.", required=False, style=InputTextStyle.long))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        title = None
        for child in self.children:
            if child.row == 0:
                title = child.value
        request = ""

        requestChannel = self.bot.get_channel(self.channel)
        embed = EmbedWithAuthorWithoutContext(self.author)
        embed.set_footer(text=f"Added by {self.author.name}")
        embed.title = title if title is not None else self.children[0].value
        if self.custom_questions is None:
            if self.children[1].value is not None:
                embed.add_field(name="Information", value=self.children[1].value, inline=False)
                request += f"Information\n{self.children[1].value}\n\n"
            if self.children[2].value is not None:
                embed.add_field(name="Who would use it?", value=self.children[2].value, inline=False)
                request += f"Who would use it?\n{self.children[2].value}\n\n"
            if self.children[3].value is not None:
                embed.add_field(name="How would it work?", value=self.children[3].value, inline=False)
                request += f"How would it work?\n{self.children[3].value}\n\n"
            if self.children[4].value is not None:
                embed.add_field(name="Why should this be added?", value=self.children[4].value, inline=False)
                request += f"Why should this be added?\n{self.children[4].value}\n\n"
        else:
            for index in range(1, len(self.children)):
                for index_child in self.children:
                    if index_child.row == index:
                        child = index_child
                question = [x for x in self.custom_questions.questions if x['position'] == index][0]
                label = question['text']
                embed.add_field(name=label, value=child.value, inline=False)
                request += f"{label}\n{child.value}\n\n"

        message = await requestChannel.send(embed=embed)

        report = await Report.new(self.author.id, self.report_id, title if title is not None else self.children[0].value,
                                  [Attachment(self.author.id, request)], is_bug=False,
                                  repo=self.repo, jumpUrl=message.jump_url, trackerId=self.tracker)

        reportMessage = await report.setup_message(self.bot, self.interaction.guild_id, report.trackerId)

        await finishReportCreation(self, interaction, report, reportMessage, requestChannel)
