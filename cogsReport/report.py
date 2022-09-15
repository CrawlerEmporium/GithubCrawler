import discord
from discord import slash_command, Option, permissions
from discord.ext import commands

from cogsReport.handle import HandleReport
from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.utils.embeds import EmbedWithAuthor
from utils.autocomplete import get_server_reports, get_server_feature_identifiers
from utils.reportglobals import ReportFromId, getAllReports

from utils import globals as GG
log = GG.log

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
    async def upvote(self, ctx, _id: Option(str, "Which report do you want to upvote?", autocomplete=get_server_feature_identifiers), msg: Option(str, "Do you have any added comment for this upvote?", default="")):
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
    async def downvote(self, ctx, _id: Option(str, "Which report do you want to downvote?", autocomplete=get_server_feature_identifiers), msg: Option(str, "Do you have any added comment for this downvote?", default="")):
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
    async def indifferent(self, ctx, _id: Option(str, "Which report do you want to be indifferent about?", autocomplete=get_server_feature_identifiers), msg: Option(str, "Do you have any added comment for the indifference?", default="")):
        """Adds an indifference to the selected report."""
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

    @slash_command(name="subscriptions")
    @permissions.guild_only()
    async def subscriptions(self, ctx):
        """Gets a list of all tickets you are subscribed to."""
        reports = await GG.MDB['Reports'].find({}).to_list(length=None)

        user = ctx.interaction.user
        subscribedReports = []

        for report in reports:
            if user.id in report.get('subscribers', []):
                rep = {
                    "report_id": report['report_id'],
                    "title": report['title'],
                    "jumpUrl": report.get('jumpUrl', "NoLink")
                }
                subscribedReports.append(rep)

        embed_queue = [EmbedWithAuthor(ctx)]
        embed_queue[-1].title = f"Your subscribed reports."

        for report in subscribedReports:
            jumpUrl = report.get("jumpUrl", "NoLink")
            if jumpUrl is not None and jumpUrl != "NoLink":
                msg_url = f"[Link]({jumpUrl})"
            else:
                msg_url = f"NoLink"
            if len(embed_queue[-1].fields) == 25 or len(embed_queue[-1]) > 5000:
                embed_queue.append(discord.Embed(colour=embed_queue[-1].colour, title=embed_queue[-1].title))
            embed_queue[-1].add_field(name=f"{report['report_id']}", value=f"{report['title']} - {msg_url}", inline=False)
        await ctx.respond(embeds=embed_queue, ephemeral=True)

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


def setup(bot):
    log.info("[Report] ReportCommands...")
    bot.add_cog(ReportCommands(bot))
