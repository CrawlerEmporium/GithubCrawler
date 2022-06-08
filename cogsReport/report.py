from discord import slash_command, Option, permissions
from discord.ext import commands

import utils.globals as GG
from cogsReport.handle import HandleReport
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.handlers import logger
from utils.autocomplete import get_server_reports
from utils.reportglobals import ReportFromId, getAllReports

log = logger.logger

class ReportCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userCache = set()

    @slash_command(name="view")
    @permissions.guild_only()
    async def view(self, ctx, _id: Option(str, "Which report do you want to view?", autocomplete=get_server_reports)):
        """Shows basic overview of requested report."""
        report = await ReportFromId(_id, ctx)
        user = ctx.interaction.user
        track_google_analytics_event("Information", f"{report.report_id}", f"{user.id}")
        interaction = await ctx.respond(f"Loading report... Please hold...")
        message_id = (await interaction.original_message()).id
        message = await interaction.channel.fetch_message(message_id)
        await report.get_reportNotes(ctx, message)

    @slash_command(name="upvote")
    @permissions.guild_only()
    async def upvote(self, ctx, _id: Option(str, "Which report do you want to upvote?", autocomplete=get_server_reports), msg: Option(str, "Do you have any added comment for this upvote?", default="")):
        """Adds an upvote to the selected report."""
        report = await ReportFromId(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await report.upvote(user.id, msg, ctx, guild_id)
        await report.commit()
        await ctx.respond(f"Added your upvote to `{report.report_id}` - {report.title}.", ephemeral=True)
        track_google_analytics_event("Upvote", f"{report.report_id}", f"{user.id}")
        await report.update(ctx, guild_id)

    @slash_command(name="downvote")
    @permissions.guild_only()
    async def downvote(self, ctx, _id: Option(str, "Which report do you want to downvote?", autocomplete=get_server_reports), msg: Option(str, "Do you have any added comment for this downvote?", default="")):
        """Adds a downvote to the selected report."""
        report = await ReportFromId(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await report.downvote(user.id, msg, ctx, guild_id)
        await report.commit()
        await ctx.respond(f"Added your downvote to `{report.report_id}` - {report.title}.", ephemeral=True)
        track_google_analytics_event("Downvote", f"{report.report_id}", f"{user.id}")
        await report.update(ctx, guild_id)

    @slash_command(name="indifferent")
    @permissions.guild_only()
    async def indifferent(self, ctx, _id: Option(str, "Which report do you want to be indifferent about?", autocomplete=get_server_reports), msg: Option(str, "Do you have any added comment for the indifference?", default="")):
        """Adds a indifference to the selected report."""
        report = await ReportFromId(_id, ctx)
        user = ctx.interaction.user
        guild_id = ctx.interaction.guild_id
        await report.indifferent(user.id, msg, ctx, guild_id)
        await report.commit()
        await ctx.respond(f"Added your indifference to `{report.report_id}` - {report.title}.", ephemeral=True)
        track_google_analytics_event("Indifference", f"{report.report_id}", f"{user.id}")
        await report.update(ctx, guild_id)

    @slash_command(name="note")
    @permissions.guild_only()
    async def note(self, ctx, _id: Option(str, "Which report do you want to add a note to?", autocomplete=get_server_reports)):
        """Adds a note to a report."""
        report = await ReportFromId(_id, ctx)
        await HandleReport.note(ctx.bot, ctx.interaction, report)

    @slash_command(name="subscribe")
    @permissions.guild_only()
    async def subscribe(self, ctx, _id: Option(str, "Which report do you want to (un)subscribe to?", autocomplete=get_server_reports)):
        """Subscribes (or unsubscribe) to a report."""
        report = await ReportFromId(_id, ctx)
        user = ctx.interaction.user
        if user.id in report.subscribers:
            report.unsubscribe(user.id)
            await ctx.respond(f"Unsubscribed from `{report.report_id}` - {report.title}.", ephemeral=True)
            track_google_analytics_event("Unsubscribe", f"{report.report_id}", f"{user.id}")
        else:
            report.subscribe(user.id)
            await ctx.respond(f"Subscribed to `{report.report_id}` - {report.title}.", ephemeral=True)
            track_google_analytics_event("Subscribe", f"{report.report_id}", f"{user.id}")
        await report.commit()

    @slash_command(name="unsuball")
    @permissions.guild_only()
    async def unsuball(self, ctx):
        """Unsubscribes from all reports."""
        reports = getAllReports()
        num_unsubbed = 0
        collection = GG.MDB['Reports']

        user = ctx.interaction.user

        for report in reports:
            if user.id in report.get('subscribers', []):
                report['subscribers'].remove(user.id)
                num_unsubbed += 1
                await collection.replace_one({"report_id": report['report_id']}, report)

        await ctx.respond(f"Unsubscribed from {num_unsubbed} reports.", ephemeral=True)

    # @commands.command(aliases=['cr'])
    # @commands.guild_only()
    # async def canrepro(self, ctx, _id, *, msg=''):
    #     """Adds reproduction to a report."""
    #     report = await Report.from_id(_id, guild_id)
    #     await report.canrepro(user.id, msg, ctx, guild_id)
    #     # report.subscribe(ctx)
    #     await report.commit()
    #     await ctx.reply(f"Added a note that you can reproduce this issue to `{report.report_id}` - {report.title}.", delete_after=5)
    #     await report.update(ctx, guild_id)
    #
    # @commands.command(aliases=['cnr'])
    # @commands.guild_only()
    # async def cannotrepro(self, ctx, _id: Option(str, "Which report do you want to view?", autocomplete=get_server_reports), msg: Option(str, "Do you have any added comment for this upvate?")):
    #     """Adds a nonreproduction to a report."""
    #     report = await ReportFromId(_id, ctx)
    #     await report.cannotrepro(user.id, msg, ctx, guild_id)
    #     # report.subscribe(ctx)
    #     await report.commit()
    #     await ctx.reply(f"Added a note that you cannot reproduce this issue to `{report.report_id}` - {report.title}.", delete_after=5)
    #     await report.update(ctx, guild_id)


def setup(bot):
    log.info("[Report] ReportCommands...")
    bot.add_cog(ReportCommands(bot))
