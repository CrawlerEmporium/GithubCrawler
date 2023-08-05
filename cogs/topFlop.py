import decimal
import time

from crawler_utilities.utils.embeds import EmbedWithRandomColor
from discord.ext import commands
from discord import NotFound, slash_command, Option
from utils import globals as GG
from utils.autocomplete import get_server_feature_identifiers

log = GG.log


async def round_down(value, decimals):
    with decimal.localcontext() as ctx:
        d = decimal.Decimal(value)
        ctx.rounding = decimal.ROUND_DOWN
        return round(d, decimals)


async def tools_specific_topflop(ctx, tickets, top, flop=False):
    async with ctx.channel.typing():
        BOOSTERMEMBERS = [x.id for x in ctx.interaction.guild.get_role(585540203704483860).members]
        T2MEMBERS = [x.id for x in ctx.interaction.guild.get_role(606989073453678602).members]
        T3MEMBERS = [x.id for x in ctx.interaction.guild.get_role(606989264051503124).members]
        serverTickets = []
        toolsTickets = []
        for ticket in tickets:
            repo = ticket.get('github_repo', None)
            if repo == "5etools/tracker":
                toolsTickets.append(ticket)
        if flop:
            await ctx.respond(f"Checking {len(toolsTickets)} suggestions for their downvotes...", delete_after=5)
        else:
            await ctx.respond(f"Checking {len(toolsTickets)} suggestions for their upvotes...", delete_after=5)
        for ticket in toolsTickets:
            if ticket['severity'] != -1:
                attachments = ticket['attachments']
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
                    "ticket_id": ticket['ticket_id'],
                    "title": ticket['title'],
                    "upvotes": upvotes,
                    "downvotes": downvotes,
                    "message": ticket['message'],
                    "rating": (0 - downvotes) + upvotes,
                    "total": downvotes + upvotes
                }
                serverTickets.append(rep)
        embed = EmbedWithRandomColor()
        if flop:
            sortedList = sorted(serverTickets, key=lambda k: k['rating'], reverse=False)
            embed.title = f"Top {top} most downvoted suggestions."
        else:
            sortedList = sorted(serverTickets, key=lambda k: k['rating'], reverse=True)
            embed.title = f"Top {top} most upvoted suggestions."
        i = 1
        channel = await ctx.bot.fetch_channel(593769144969723914)
        for ticket in sortedList[:top]:
            try:
                message = await channel.fetch_message(ticket['message'])
                msg_url = f"[Link]({message.jump_url})"
            except:
                msg_url = f"No Link"

            perc = 100 * float(ticket['upvotes']) / float(ticket['total'])
            percRounded = await round_down(perc, 2)

            embed.add_field(name=f"**[#{i}] {ticket['rating']}** points ({str(percRounded)}% upvotes)",
                            value=f"{ticket['ticket_id']}: {ticket['title']} - {msg_url}", inline=False)
            i += 1
        return await ctx.respond(embed=embed)


class TopFlop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @slash_command(name="top")
    @commands.guild_only()
    async def top(self, ctx, identifier: Option(str, "From which identifier would you like a top X?", autocomplete=get_server_feature_identifiers, default=None, required=False), top: Option(int, "The top of how many?", max_value=25, min_value=10, default=10, required=False)):
        """Gets top x or top 10"""
        await ctx.defer()
        tickets, results = await self.getResults(ctx, identifier)

        if ctx.interaction.guild_id == 363680385336606740 and identifier is None:
            return await tools_specific_topflop(ctx, tickets, top)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.interaction.guild_id)
            server = guild.listen[0].repo
        except:
            return await ctx.respond("Your server isn't registered or doesn't have any channels set up yet.")

        if identifier is None:
            embed, sortedList, top = await self.getCount(ctx, guild, tickets, server, top, "upvote")
        else:
            embed, sortedList, top = await self.getCount(ctx, guild, results, server, top, "upvote")

        i = 1
        for ticket in sortedList[:top]:
            jumpUrl = ticket.get("jumpUrl", "NoLink")
            if jumpUrl is not None and jumpUrl != "NoLink":
                msg_url = f"[Link]({jumpUrl})"
            else:
                msg_url = f"NoLink"
            embed.add_field(name=f"**[#{i}] {ticket['upvotes']}** upvotes",
                            value=f"{ticket['ticket_id']}: {ticket['title']} - {msg_url}", inline=False)
            i += 1
        await ctx.respond(embed=embed)

    @slash_command(name="flop")
    @commands.guild_only()
    async def flop(self, ctx, identifier: Option(str, "From which identifier would you like a flop X?", autocomplete=get_server_feature_identifiers, default=None, required=False), top: Option(int, "The flop of how many?", max_value=25, min_value=10, default=10, required=False)):
        """Gets top x or top 10"""
        # -2 in attachment
        await ctx.defer()
        tickets, results = await self.getResults(ctx, identifier)

        if ctx.interaction.guild_id == 363680385336606740 and identifier is None:
            return await tools_specific_topflop(ctx, tickets, top, flop=True)

        try:
            guild = next(item for item in GG.GITHUBSERVERS if item.server == ctx.interaction.guild_id)
            server = guild.listen[0].repo
        except:
            return await ctx.respond("Your server isn't registered or doesn't have any channels set up yet.")

        if identifier is None:
            embed, sortedList, top = await self.getCount(ctx, guild, tickets, server, top, "downvote")
        else:
            embed, sortedList, top = await self.getCount(ctx, guild, results, server, top, "downvote")

        i = 1
        for ticket in sortedList[:top]:
            jumpUrl = ticket.get("jumpUrl", "NoLink")
            if jumpUrl is not None and jumpUrl != "NoLink":
                msg_url = f"[Link]({jumpUrl})"
            else:
                msg_url = f"NoLink"

            embed.add_field(name=f"**[#{i}] {ticket['downvotes']}** downvotes",
                            value=f"{ticket['ticket_id']}: {ticket['title']} - {msg_url}", inline=False)
            i += 1
        await ctx.respond(embed=embed)

    async def getResults(self, ctx, identifier):
        tickets = await GG.MDB.Tickets.find({}).to_list(length=None)
        results = []
        if identifier is not None:
            server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
            for iden in server['listen']:
                if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                    identifier = iden['identifier']

            for x in tickets:
                if identifier.upper() in x['ticket_id']:
                    results.append(x)
            tickets = results
        return tickets, results

    async def getCount(self, ctx, guild, tickets, server, top, type):
        serverTickets = []
        if server is not None:
            for ticket in tickets:
                repo = ticket.get('github_repo', None)
                if server == repo or server == "5etools/tracker":
                    if ticket['severity'] != -1:
                        rep = {
                            "ticket_id": ticket['ticket_id'],
                            "title": ticket['title'],
                            f"{type}s": ticket[f'{type}s'],
                            "jumpUrl": ticket.get('jumpUrl', "NoLink")
                        }
                        serverTickets.append(rep)
        else:
            trackerChannels = []
            for x in guild.listen:
                trackerChannels.append(x.tracker)
            for ticket in tickets:
                tracker = ticket.get('trackerId', None)
                if tracker in trackerChannels:
                    if ticket['severity'] != -1:
                        rep = {
                            "ticket_id": ticket['ticket_id'],
                            "title": ticket['title'],
                            f"{type}s": ticket[f'{type}s'],
                            "jumpUrl": ticket.get('jumpUrl', "NoLink")
                        }
                        serverTickets.append(rep)

        sortedList = sorted(serverTickets, key=lambda k: k[f'{type}s'], reverse=True)
        embed = EmbedWithRandomColor()
        embed.title = f"Top {top} most {type}d suggestions."
        return embed, sortedList, top


def setup(bot):
    log.info("[Cogs] TopFlop...")
    bot.add_cog(TopFlop(bot))
