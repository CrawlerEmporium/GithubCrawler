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

class ReportCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="view")
    async def view(self, ctx, _id: Option(str, "Which report do you want to view?", autocomplete=get_server_reports)):
        """Shows basic overview of requested report."""
        report = await Report.from_id(_id, ctx.guild.id)
        await report.get_reportNotes(ctx, True)
        track_google_analytics_event("Information", f"{report.report_id}", f"{ctx.author.id}")


def setup(bot):
    log.info("[Report] ReportCommands...")
    bot.add_cog(ReportCommands(bot))
