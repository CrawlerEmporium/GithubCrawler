import decimal
import time

from crawler_utilities.utils.embeds import EmbedWithAuthor
from discord.ext import commands
from discord import NotFound, slash_command, Option
from utils import globals as GG
from utils.autocomplete import get_server_identifiers

log = GG.log


async def round_down(value, decimals):
    with decimal.localcontext() as ctx:
        d = decimal.Decimal(value)
        ctx.rounding = decimal.ROUND_DOWN
        return round(d, decimals)


class TopFlop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @slash_command(name="top")
    @commands.guild_only()
    async def top(self, ctx, identifier: Option(str, "From which identifier would you like a top X?", autocomplete=get_server_identifiers, default=None, required=False), top: Option(int, "The top of how many?", max_value=25, min_value=10, default=10, required=False)):
        """Gets top x or top 10"""
        await ctx.defer(ephemeral=True)
        reports, results = await self.getResults(identifier)

        if ctx.interaction.guild_id == 363680385336606740 and identifier is None:
            return await self.tools_specific_topflop(ctx, reports, top)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.guild.id)
            server = guild.listen[0].repo
        except:
            return await ctx.respond("Your server isn't registered or doesn't have any channels set up yet.", ephemeral=True)

        if identifier is None:
            embed, sortedList, top = await self.getCount(ctx, guild, reports, server, top, "upvote")
        else:
            embed, sortedList, top = await self.getCount(ctx, guild, results, server, top, "upvote")

        i = 1
        for report in sortedList[:top]:
            embed.add_field(name=f"**#{i} - {report['upvotes']}** upvotes",
                            value=f"{report['report_id']}: {report['title']}", inline=False)
            i += 1
        await ctx.respond(embed=embed)

    @slash_command(name="flop")
    @commands.guild_only()
    async def flop(self, ctx, identifier: Option(str, "From which identifier would you like a flop X?", autocomplete=get_server_identifiers, default=None, required=False), top: Option(int, "The flop of how many?", max_value=25, min_value=10, default=10, required=False)):
        """Gets top x or top 10"""
        # -2 in attachment
        await ctx.defer(ephemeral=True)
        reports, results = await self.getResults(identifier)

        if ctx.guild.id == 363680385336606740 and identifier is None:
            return await self.tools_specific_topflop(ctx, reports, top, flop=True)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.guild.id)
            server = guild.listen[0].repo
        except:
            return await ctx.respond("Your server isn't registered or doesn't have any channels set up yet.", ephemeral=True)

        if identifier is None:
            embed, sortedList, top = await self.getCount(ctx, guild, reports, server, top, "downvote")
        else:
            embed, sortedList, top = await self.getCount(ctx, guild, results, server, top, "downvote")

        i = 1
        for report in sortedList[:top]:
            embed.add_field(name=f"**#{i} - {report['downvotes']}** downvotes",
                            value=f"{report['report_id']}: {report['title']}", inline=False)
            i += 1
        await ctx.respond(embed=embed)

    async def getResults(self, identifier):
        reports = await GG.MDB.Reports.find({}).to_list(length=None)
        results = []
        if identifier is not None:
            for x in reports:
                if identifier.upper() in x['report_id']:
                    results.append(x)
        reports = results
        return reports, results

    async def getCount(self, ctx, guild, reports, server, top, type):
        serverReports = []
        if server is not None:
            for report in reports:
                repo = report.get('github_repo', None)
                if server == repo or server == "5etools/tracker":
                    if report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            f"{type}s": report[f'{type}s']
                        }
                        serverReports.append(rep)
        else:
            trackerChannels = []
            for x in guild.listen:
                trackerChannels.append(x.tracker)
            for report in reports:
                tracker = report.get('trackerId', None)
                if tracker in trackerChannels:
                    if report['severity'] != -1:
                        rep = {
                            "report_id": report['report_id'],
                            "title": report['title'],
                            f"{type}s": report[f'{type}s']
                        }
                        serverReports.append(rep)

        sortedList = sorted(serverReports, key=lambda k: k[f'{type}s'], reverse=True)
        embed = EmbedWithAuthor(ctx)
        embed.title = f"Top {top} most {type}d suggestions."
        return embed, sortedList, top

    async def tools_specific_topflop(self, ctx, reports, top, flop=False):
        async with ctx.channel.typing():
            BOOSTERMEMBERS = [x.id for x in ctx.guild.get_role(585540203704483860).members]
            T2MEMBERS = [x.id for x in ctx.guild.get_role(606989073453678602).members]
            T3MEMBERS = [x.id for x in ctx.guild.get_role(606989264051503124).members]
            serverReports = []
            toolsReports = []
            for report in reports:
                repo = report.get('github_repo', None)
                if repo == "5etools/tracker":
                    toolsReports.append(report)
            if flop:
                await ctx.respond(f"Checking {len(toolsReports)} suggestions for their downvotes...", delete_after=5)
            else:
                await ctx.respond(f"Checking {len(toolsReports)} suggestions for their upvotes...", delete_after=5)
            for report in toolsReports:
                if report['severity'] != -1:
                    attachments = report['attachments']
                    upvotes = 0
                    downvotes = 0
                    for attachment in attachments:
                        if attachment['veri'] == -2:
                            try:
                                if attachment['author'] in BOOSTERMEMBERS or attachment['author'] in T2MEMBERS:
                                    downvotes += 1
                                if attachment['author'] in T3MEMBERS:
                                    downvotes += 2
                                downvotes += 1
                            except NotFound:
                                downvotes += 1
                        if attachment['veri'] == 2:
                            try:
                                if attachment['author'] in BOOSTERMEMBERS or attachment['author'] in T2MEMBERS:
                                    upvotes += 1
                                if attachment['author'] in T3MEMBERS:
                                    upvotes += 2
                                upvotes += 1
                            except NotFound:
                                upvotes += 1
                    rep = {
                        "report_id": report['report_id'],
                        "title": report['title'],
                        "upvotes": upvotes,
                        "downvotes": downvotes,
                        "message": report['message'],
                        "rating": (0 - downvotes) + upvotes,
                        "total": downvotes + upvotes
                    }
                    serverReports.append(rep)
            embed = EmbedWithAuthor(ctx)
            if flop:
                sortedList = sorted(serverReports, key=lambda k: k['rating'], reverse=False)
                embed.title = f"Top {top} most downvoted suggestions."
            else:
                sortedList = sorted(serverReports, key=lambda k: k['rating'], reverse=True)
                embed.title = f"Top {top} most upvoted suggestions."
            i = 1
            channel = await ctx.bot.fetch_channel(593769144969723914)
            for report in sortedList[:top]:
                try:
                    message = await channel.fetch_message(report['message'])
                    msg_url = f"[Link]({message.jump_url})"
                except:
                    msg_url = f"No Link"

                perc = 100 * float(report['upvotes']) / float(report['total'])
                percRounded = await round_down(perc, 2)

                embed.add_field(name=f"**#{i} - {report['rating']}** points ({str(percRounded)}% upvotes)",
                                value=f"{report['report_id']}: {report['title']} - {msg_url}", inline=False)
                i += 1
            return await ctx.respond(embed=embed)


def setup(bot):
    log.info("[Cogs] TopFlop...")
    bot.add_cog(TopFlop(bot))
