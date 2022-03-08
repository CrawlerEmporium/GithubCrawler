import discord
from discord import InputTextStyle, Interaction
from discord.ui import Modal, InputText

from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.utils.embeds import EmbedWithAuthorWithoutContext
from models.attachment import Attachment
from models.questions import Questionaire
from models.reports import Report
import utils.globals as GG


class Bug(Modal):
    def __init__(self, identifier, bot, interaction, report_id, author, repo, tracker, channel, custom_questions: Questionaire = None) -> None:
        super().__init__(f"{identifier}: Bug Report")

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
            self.add_item(InputText(label="What is the bug?", placeholder="A quick description of the bug.", required=True))
            self.add_item(InputText(label="Steps to reproduce", placeholder="How the bug occured, and how to reproduce it.", required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Severity", placeholder="Trivial / Low / Medium / High / Critical", required=True, style=InputTextStyle.long))
            self.add_item(InputText(label="Additional information", placeholder="Any additional information you want to give.", required=False, style=InputTextStyle.long))

    async def callback(self, interaction: Interaction):
        title = f"{self.children[0].value}"
        request = ""

        requestChannel = self.bot.get_channel(self.channel)
        embed = EmbedWithAuthorWithoutContext(self.author)
        embed.set_footer(text=f"Added by {self.author.name}")

        if self.custom_questions is None:
            if self.children[1].value is not None:
                embed.add_field(name="Steps to reproduce", value=self.children[1].value, inline=False)
                request += f"Steps to reproduce\n{self.children[1].value}\n\n"
            if self.children[2].value is not None:
                embed.add_field(name="Severity", value=self.children[2].value, inline=False)
                request += f"Severity\n{self.children[2].value}\n\n"
            if self.children[3].value is not None:
                embed.add_field(name="Additional information", value=self.children[3].value, inline=False)
                request += f"Additional information\n{self.children[3].value}\n\n"
        else:
            i = 0
            for child in self.children:
                question = [x for x in self.custom_questions.questions if x['position'] == i][0]
                label = question['text']
                embed.add_field(name=label, value=child.value, inline=False)
                request += f"{label}\n{child.value}\n\n"
                i += 1

        message = await requestChannel.send(embed=embed)

        report = await Report.new(self.author.id, self.report_id, title,
                                  [Attachment(self.author.id, request)], is_bug=True,
                                  repo=self.repo, jumpUrl=message.jump_url, trackerId=self.channel)

        if interaction.guild_id in GG.SERVERS:
            if self.repo is not None:
                await report.setup_github(await self.bot.get_context(message), message.guild.id)

        reportMessage = await report.setup_message(self.bot, self.interaction.guild_id, report.trackerId)

        track_google_analytics_event("Bug Report", f"{self.report_id}", f"{self.author.id}")

        await report.commit()

        prefix = await self.bot.get_guild_prefix(self.interaction.message)

        embed = discord.Embed()
        embed.title = f"Your submission ``{self.report_id}`` was accepted."
        embed.add_field(name="Status Checking", value=f"To check on its status: `{prefix}report {self.report_id}`.",
                        inline=False)
        embed.add_field(name="Note Adding",
                        value=f"To add a note: `{prefix}note {self.report_id} <comment>`.",
                        inline=False)
        embed.add_field(name="Subscribing",
                        value=f"To subscribe: `{prefix}subscribe {self.report_id}`. (This is only for others, the submittee is automatically subscribed).",
                        inline=False)
        embed.add_field(name="Voting",
                        value=f"You can find the report here: [Click me]({reportMessage.jump_url})",
                        inline=False)

        await requestChannel.send(embed=embed)

        await interaction.response.send_message(f"Your feature request was sucessfully posted in <#{requestChannel.id}>!", ephemeral=True)
