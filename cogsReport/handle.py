from discord import Interaction
from discord.ext import commands

import utils.globals as GG
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.handlers import logger
from models.reports import Report, ReportException
from utils.checks import isManagerAssigneeOrReporterButton
from utils.reportglobals import UPVOTE, DOWNVOTE, SHRUG, SUBSCRIBE, RESOLVE, INFORMATION

log = logger.logger


class HandleReport(commands.Cog):
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

        if label not in (UPVOTE, DOWNVOTE, INFORMATION, SHRUG, SUBSCRIBE, RESOLVE) or member.bot or label is None:
            return

        try:
            report = await Report.from_message_id(message.id)
        except ReportException:
            return

        if label == INFORMATION:
            track_google_analytics_event("Information", f"{report.report_id}", f"{member.id}")

        if report.is_bug:
            await self.handle_bug(self.bot, interaction, label, member, report, server)

        if not report.is_bug:
            if server.owner_id == member.id:
                await self.handle_feature_server_owner(self.bot, interaction, label, member, report, server)
            else:
                await self.handle_feature_user(self.bot, interaction, label, member, message, report, server)

        await report.commit()
        await report.update(GG.ContextProxy(self.bot, interaction=interaction), server.id)

    @staticmethod
    async def handle_feature_user(bot, interaction, label, member, message, report, server):
        try:
            if label == UPVOTE:
                print(f"Upvote: {member} - {report.report_id}")
                await report.upvote(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have upvoted {report.report_id}", ephemeral=True)
            elif label == INFORMATION:
                print(f"Information: {member} - {report.report_id}")
                em = await report.get_embed(True)
                await interaction.response.send_message(embed=em, ephemeral=True)
            elif label == SHRUG:
                print(f"Shrugged: {member} - {report.report_id}")
                await report.indifferent(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have shown indifference for {report.report_id}", ephemeral=True)
            elif label == SUBSCRIBE:
                await HandleReport.subscribe(interaction, member, report)
            elif label == RESOLVE:
                await HandleReport.resolve(bot, interaction, member, report, server)
            else:
                print(f"Downvote: {member} - {report.report_id}")
                await report.downvote(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
                await interaction.response.send_message(content=f"You have downvoted {report.report_id}", ephemeral=True)
        except ReportException as e:
            if interaction.channel == message.channel:
                await interaction.response.send_message(content=str(e), ephemeral=True)
            else:
                await member.send(str(e))
                await interaction.response.defer()

    @staticmethod
    async def handle_feature_server_owner(bot, interaction, label, member, report, server):
        if label == UPVOTE:
            print(f"Upvote: {member} - {report.report_id}")
            await report.force_accept(GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have accepted {report.report_id}", ephemeral=True)
        elif label == INFORMATION:
            print(f"Information: {member} - {report.report_id}")
            em = await report.get_embed(True)
            await interaction.response.send_message(embed=em, ephemeral=True)
        elif label == SHRUG:
            print(f"Shrugged: {member} - {report.report_id}")
            await report.indifferent(member.id, '', GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have shown indifference for {report.report_id}", ephemeral=True)
        elif label == SUBSCRIBE:
            await HandleReport.subscribe(interaction, member, report)
        elif label == RESOLVE:
            await report.resolve(GG.ContextProxy(bot, interaction=interaction, message=GG.FakeAuthor(member)), server.id, "Report closed.")
            await interaction.response.send_message(content=f"You have resolved {report.report_id}", ephemeral=True)
            await report.commit()
        else:
            await report.force_deny(GG.ContextProxy(bot, interaction=interaction), server.id)
            await interaction.response.send_message(content=f"You have denied {report.report_id}", ephemeral=True)
            await report.commit()

    @staticmethod
    async def handle_bug(bot, interaction, label, member, report, server):
        if label == INFORMATION:
            print(f"Information: {member} - {report.report_id}")
            em = await report.get_embed(True)
            await interaction.response.send_message(embed=em, ephemeral=True)
        elif label == SUBSCRIBE:
            await HandleReport.subscribe(interaction, member, report)
        elif label == RESOLVE:
            await HandleReport.resolve(bot, interaction, member, report, server)

    @staticmethod
    async def resolve(bot, interaction, member, report, server):
        if await isManagerAssigneeOrReporterButton(member.id, server.id, report, bot):
            await report.resolve(GG.ContextProxy(bot, interaction=interaction, message=GG.FakeAuthor(member)), server.id, "Report closed.")
            await report.commit()
        else:
            await interaction.response.send_message(content=f"You do not have permissions to resolve/close this.", ephemeral=True)

    @staticmethod
    async def subscribe(interaction, member, report):
        if member.id in report.subscribers:
            report.unsubscribe(member.id)
            await interaction.response.send_message(content=f"You have unsubscribed from {report.report_id}", ephemeral=True)
        else:
            report.subscribe(member.id)
            await interaction.response.send_message(content=f"You have subscribed to {report.report_id}", ephemeral=True)


def setup(bot):
    log.info("[Report] HandleReport...")
    bot.add_cog(HandleReport(bot))