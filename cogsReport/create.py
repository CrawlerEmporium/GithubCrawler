import asyncio
import copy
import typing
import re

import discord
from discord import slash_command, Option
from discord.ext import commands

import utils.globals as GG
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.utils.confirmation import BotConfirmation
from crawler_utilities.utils.pagination import BotEmbedPaginator
from modal.bug import Bug
from modal.feature import Feature
from models.milestone import Milestone, MilestoneException
from crawler_utilities.handlers import logger
from models.questions import Question, Questionaire
from utils.autocomplete import get_server_feature_identifiers, get_server_identifiers, get_server_bug_identifiers, \
    get_server_reports
from utils.checks import isManager, isAssignee, isReporter, isManagerAssigneeOrReporterButton, isManagerSlash
from utils.functions import get_settings
from models.reports import get_next_report_num, Report, ReportException, Attachment, UPVOTE_REACTION, \
    DOWNVOTE_REACTION, INFORMATION_REACTION, SHRUG_REACTION

log = logger.logger

class CreateReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="questionnaire")
    async def slash_questionnaire(self, ctx,
                                  identifier: Option(str, "For what identifier do you want to add questions?", autocomplete=get_server_identifiers),
                                  position: Option(int, "In what position? (Between 1 and 5)", min_value=1, max_value=5),
                                  required: Option(bool, "Is the question required?"),
                                  style: Option(str, "What input style?", choices=["Singleline", "Multiline"]),
                                  label: Option(str, "What's the question?"),
                                  placeholder: Option(str, "Optional text inside the input box. (Max 100 characters.)", default="")
                                  ):
        """Create questions for feature requests and bug reports."""
        if not await isManagerSlash(ctx.interaction.user.id, ctx.interaction.guild_id):
            return await ctx.interaction.response.send_message("You do not have the required permissions to use this command.", ephemeral=True)

        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier:
                identifier = iden['identifier']
                exists = True

        if not exists:
            return await ctx.interaction.response.send_message(f"The identifier ``{identifier}`` could not be found.\n"
                                                               f"If the identifier was shown in the option box, please contact the developer of the bot through the ``!support`` command.\n\n"
                                                               f"Otherwise this command can only be used on servers that have the feature request functionality of the bot enabled.", ephemeral=True)

        if style == "Singleline":
            style = 1
        else:
            style = 2

        question = Question(position - 1, label, placeholder, style, required)

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        if questionaire is None:
            questionaire = Questionaire(ctx.interaction.guild_id, identifier)

        duplicate = await questionaire.add_question(question)
        if duplicate is False:
            confirmation = BotConfirmation(ctx, 0x012345)
            try:
                channel = await self.bot.fetch_channel(ctx.interaction.channel_id)
            except Exception:
                return await ctx.respond(f"I tried posting a confirmation box in this channel, but I don't have access to this channel\nPlease try it in a channel where I have send message permissions.", ephemeral=True)
            await ctx.defer(ephemeral=True)
            await confirmation.confirm(f"A question in this position already exists, do you want to overwrite it?", channel=channel)
            if confirmation.confirmed:
                await confirmation.update(f"Confirmed, overwriting question..", color=0x55ff55)
                await asyncio.sleep(2)
                await confirmation.quit()
                await questionaire.add_question(question, True)
                await ctx.respond(f"Question ``{label}`` added for ``{identifier}``", ephemeral=True)
            else:
                await confirmation.quit()
                await ctx.respond("Question wasn't added.", ephemeral=True)
        else:
            await ctx.respond(f"Question ``{label}`` added for ``{identifier}``", ephemeral=True)

    @slash_command(name="featurerequest")
    async def slash_featurerequest(self, ctx, identifier: Option(str, "For what identifier do you want to make a feature request?", autocomplete=get_server_feature_identifiers)):
        """Opens a modal to post a feature request."""
        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier:
                identifier = iden['identifier']
                repo = iden['repo']
                tracker = iden['tracker']
                channel = iden['channel']
                if iden['type'] == "feature":
                    exists = True

        if not exists:
            return await ctx.interaction.response.send_message(f"The identifier ``{identifier}`` could not be found.\n"
                                                               f"If the identifier was shown in the option box, please contact the developer of the bot through the ``!support`` command.\n\n"
                                                               f"Otherwise this command can only be used on servers that have the feature request functionality of the bot enabled.", ephemeral=True)

        if identifier is not None:
            try:
                report_num = await get_next_report_num(identifier, ctx.guild.id)
            except ReportException as e:
                return await ctx.interaction.response.send_message(e, ephemeral=True)

        report_id = f"{identifier}-{report_num}"

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        modal = Feature(identifier, self.bot, ctx.interaction, report_id, ctx.interaction.user, repo, tracker, channel, questionaire)
        await ctx.interaction.response.send_modal(modal)

    @slash_command(name="bug")
    async def slash_bug(self, ctx, identifier: Option(str, "For what identifier do you want to make a bug report?", autocomplete=get_server_bug_identifiers)):
        """Opens a modal to post a bug report."""
        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier:
                identifier = iden['identifier']
                repo = iden['repo']
                tracker = iden['tracker']
                channel = iden['channel']
                if iden['type'] == "bug":
                    exists = True

        if not exists:
            return await ctx.interaction.response.send_message(f"The identifier ``{identifier}`` could not be found.\n"
                                                               f"If the identifier was shown in the option box, please contact the developer of the bot through the ``!support`` command.\n\n"
                                                               f"Otherwise this command can only be used on servers that have the bug reports functionality of the bot enabled.", ephemeral=True)


        if identifier is not None:
            try:
                report_num = await get_next_report_num(identifier, ctx.guild.id)
            except ReportException as e:
                return await ctx.interaction.response.send_message(e, ephemeral=True)

        report_id = f"{identifier}-{report_num}"

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        modal = Bug(identifier, self.bot, ctx.interaction, report_id, ctx.interaction.user, repo, tracker, channel, questionaire)
        await ctx.interaction.response.send_modal(modal)


def setup(bot):
    log.info("[Report] CreateReport...")
    bot.add_cog(CreateReport(bot))
