from discord.ext import commands

import utils.globals as GG
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.handlers import logger
from models.reports import Report, ReportException, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION, SHRUG_REACTION
from utils.checks import isManagerAssigneeOrReporterButton
from utils.reportglobals import UPVOTE, DOWNVOTE, SHRUG, SUBSCRIBE, RESOLVE, INFORMATION

log = logger.logger


class HandleReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event):
        if not event.guild_id:
            return

        msg_id = event.message_id
        server = self.bot.get_guild(event.guild_id)
        member = server.get_member(event.user_id)
        emoji = event.emoji

        await self.handle_reaction(msg_id, member, emoji, server)

    async def handle_reaction(self, msg_id, member, emoji, server):
        if emoji.name not in (UPVOTE_REACTION, DOWNVOTE_REACTION, INFORMATION_REACTION, SHRUG_REACTION):
            return

        try:
            report = await Report.from_message_id(msg_id)
        except ReportException:
            return

        if member.bot:
            return
        if report.is_bug:
            if emoji.name == INFORMATION_REACTION:
                print(f"Information: {member} - {report.report_id}")
                em = await report.get_embed(True)
                if member.dm_channel is not None:
                    DM = member.dm_channel
                else:
                    DM = await member.create_dm()
                try:
                    await DM.send(embed=em)
                except:
                    pass
            else:
                return

        if server.owner_id == member.id:
            if emoji.name == UPVOTE_REACTION:
                await report.force_accept(GG.ContextProxy(self.bot), server.id)
            elif emoji.name == INFORMATION_REACTION:
                em = await report.get_embed(True)
                if member.dm_channel is not None:
                    DM = member.dm_channel
                else:
                    DM = await member.create_dm()
                try:
                    await DM.send(embed=em)
                except:
                    pass
            else:
                log.info(f"Force denying {report.title}")
                await report.force_deny(GG.ContextProxy(self.bot), server.id)
                await report.commit()
                return
        else:
            try:
                if emoji.name == UPVOTE_REACTION:
                    print(f"Upvote: {member} - {report.report_id}")
                    await report.upvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                elif emoji.name == INFORMATION_REACTION:
                    print(f"Information: {member} - {report.report_id}")
                    em = await report.get_embed(True)
                    if member.dm_channel is not None:
                        DM = member.dm_channel
                    else:
                        DM = await member.create_dm()
                    try:
                        await DM.send(embed=em)
                    except:
                        pass
                elif emoji.name == SHRUG_REACTION:
                    print(f"Shrugged: {member} - {report.report_id}")
                    await report.indifferent(member.id, '', GG.ContextProxy(self.bot), server.id)
                else:
                    print(f"Downvote: {member} - {report.report_id}")
                    await report.downvote(member.id, '', GG.ContextProxy(self.bot), server.id)
            except ReportException as e:
                await member.send(str(e))

        await report.commit()
        await report.update(GG.ContextProxy(self.bot), server.id)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
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
        if label is None:
            return
        await self.handle_button(interaction.message, interaction.user, label, interaction.guild, interaction)

    async def handle_button(self, message, member, label, server, interaction):
        if label not in (UPVOTE, DOWNVOTE, INFORMATION, SHRUG, SUBSCRIBE, RESOLVE):
            return

        try:
            report = await Report.from_message_id(message.id)
        except ReportException:
            return

        if member.bot:
            return

        if label == INFORMATION:
            track_google_analytics_event("Information", f"{report.report_id}", f"{member.id}")

        if report.is_bug:
            if label == INFORMATION:
                print(f"Information: {member} - {report.report_id}")
                em = await report.get_embed(True)
                await interaction.response.send_message(embed=em, ephemeral=True)
            elif label == SUBSCRIBE:
                if member.id in report.subscribers:
                    report.unsubscribe(member.id)
                    await interaction.response.send_message(content=f"You have unsubscribed from {report.report_id}",
                                                            ephemeral=True)
                else:
                    report.subscribe(member.id)
                    await interaction.response.send_message(content=f"You have subscribed to {report.report_id}",
                                                            ephemeral=True)
            elif label == RESOLVE:
                if await isManagerAssigneeOrReporterButton(member.id, server.id, report, self.bot):
                    await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id,
                                         "Report closed.")
                    await report.commit()
                else:
                    await interaction.response.send_message(
                        content=f"You do not have permissions to resolve/close this.", ephemeral=True)
            else:
                return

        if not report.is_bug:
            if server.owner_id == member.id:
                if label == UPVOTE:
                    await report.force_accept(GG.ContextProxy(self.bot), server.id)
                    await interaction.response.send_message(content=f"You have accepted {report.report_id}",
                                                            ephemeral=True)
                elif label == INFORMATION:
                    em = await report.get_embed(True)
                    await interaction.response.send_message(embed=em, ephemeral=True)
                elif label == SHRUG:
                    pass
                elif label == SUBSCRIBE:
                    pass
                elif label == RESOLVE:
                    await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id,
                                         "Report closed.")
                    await report.commit()
                else:
                    log.info(f"Force denying {report.title}")
                    await report.force_deny(GG.ContextProxy(self.bot), server.id)
                    await report.commit()
            else:
                try:
                    if label == UPVOTE:
                        print(f"Upvote: {member} - {report.report_id}")
                        await report.upvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await interaction.response.send_message(content=f"You have upvoted {report.report_id}",
                                                                ephemeral=True)
                    elif label == INFORMATION:
                        print(f"Information: {member} - {report.report_id}")
                        em = await report.get_embed(True)
                        await interaction.response.send_message(embed=em, ephemeral=True)
                    elif label == SHRUG:
                        print(f"Shrugged: {member} - {report.report_id}")
                        await report.indifferent(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await interaction.response.send_message(
                            content=f"You have shown indifference for {report.report_id}", ephemeral=True)
                    elif label == SUBSCRIBE:
                        if member.id in report.subscribers:
                            report.unsubscribe(member.id)
                            await interaction.response.send_message(
                                content=f"You have unsubscribed from {report.report_id}", ephemeral=True)
                        else:
                            report.subscribe(member.id)
                            await interaction.response.send_message(
                                content=f"You have subscribed to {report.report_id}", ephemeral=True)
                    elif label == RESOLVE:
                        if await isManagerAssigneeOrReporterButton(member.id, server.id, report, self.bot):
                            await report.resolve(GG.ContextProxy(self.bot, message=GG.FakeAuthor(member)), server.id,
                                                 "Report closed.")
                            await report.commit()
                        else:
                            await interaction.response.send_message(
                                content=f"You do not have permissions to resolve/close this.", ephemeral=True)
                    else:
                        print(f"Downvote: {member} - {report.report_id}")
                        await report.downvote(member.id, '', GG.ContextProxy(self.bot), server.id)
                        await interaction.response.send_message(content=f"You have downvoted {report.report_id}",
                                                                ephemeral=True)
                except ReportException as e:
                    if interaction.channel == message.channel:
                        await interaction.response.send_message(content=str(e), ephemeral=True)
                    else:
                        await member.send(str(e))
                        await interaction.response.defer()

        await report.commit()
        await report.update(GG.ContextProxy(self.bot), server.id)


def setup(bot):
    log.info("[Report] HandleReport...")
    bot.add_cog(HandleReport(bot))
