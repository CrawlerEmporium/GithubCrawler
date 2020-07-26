from discord.ext import commands

import utils.globals as GG
from models.server import Server, Listen
from utils import logger
from utils.functions import loadGithubServers

log = logger.logger

TYPES = ['bug', 'feature']


class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def issue(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```{prefix}issue\n"
                       f"{prefix}issue trackers\n"
                       f"{prefix}issue register\n"
                       f"{prefix}issue channel <type> <identifier> [tracker=0] [channel=0]```")

    @issue.command(name='register')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def register(self, ctx):
        guild = ctx.guild
        server = guild.id
        admin = guild.owner.id
        name = guild.name
        exist = await GG.MDB.Github.find_one({"server": server})
        if exist is None:
            gh = Server(name, server, admin, None, [], 5)
            await GG.MDB.Github.insert_one(gh.to_dict())
            await loadGithubServers()
            await ctx.send("Server was added to the database. You can now use the other commands.")
        else:
            await ctx.send("Server already exists in the database. Use the TODO command to check your info.")

    @issue.command(name='channel')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx, type: str, identifier: str, tracker: int = 0, channel: int = 0):
        """
        Adds a new listener/tracker for the bot.
        Usage:
        type = 'bug' or 'feature'
        identifier = what you want your prefix to be
        tracker = OPTIONAL ChannelID of the channel you want as your posting channel, will create a new channel if not supplied.

        channel = OPTIONAL ChannelID of the channel you want as your listening channel, will create a new channel if not supplied.
        """
        if type not in TYPES:
            await ctx.send("Currently you can only use ``bug`` or ``feature``.")
            return

        # CHECK IDENTIFIER
        identifier = identifier.upper()
        exist = await GG.MDB.ReportNums.find_one({"key": identifier})
        if exist is not None:
            await ctx.send(
                "This identifier is already in use (either by you, or by a different server), please select another one.")
            return
        await GG.MDB.ReportNums.insert_one({"key": identifier, "amount": 0})

        # CREATE CHANNELS
        if channel == 0:
            channel = await ctx.guild.create_text_channel(f"{identifier}-listener")
        else:
            channel = self.bot.get_channel(channel)

        if tracker == 0:
            tracker = await ctx.guild.create_text_channel(f"{identifier}-tracker")
        else:
            tracker = self.bot.get_channel(tracker)

        # ADD LISTENER TO THE SERVER
        if channel is not None and tracker is not None:
            listener = Listen(channel.id, tracker.id, identifier, type, None)
            data = await GG.MDB.Github.find_one({"server": ctx.guild.id})
            server = Server.from_data(data)
            listener = listener.to_dict()
            server = server.to_dict()
            oldListen = []
            for x in server['listen']:
                oldListen.append(x.to_dict())
            server['listen'] = oldListen
            server['listen'].append(listener)
            await GG.MDB.Github.replace_one({"server": ctx.guild.id}, server)
            await loadGithubServers()
        else:
            await ctx.send("The given channel or tracker ID's are invalid.")
            return

        # SEND MESSAGE TO NEW CHANNELS
        msgChannel = self.bot.get_channel(channel.id)
        if type == 'bug':
            await msgChannel.send(
                "If you have a bug, you can use the below posted template. Otherwise the bot will **NOT** pick it "
                "up.\n\n```**What is the bug?**: A quick description of the bug.\n\n**Severity**: Trivial (typos, "
                "etc) / Low (formatting issues, things that don't impact operation) / Medium (minor functional "
                "impact) / High (a broken feature, major functional impact) / Critical (bot crash, extremely major "
                "functional impact)\n\n**Steps to reproduce**: How the bug occured, and how to reproduce it. I cannot "
                "bugfix without this.\n\n**Context**: The command run that the bug occured in and any choice "
                "trees.```")
        if type == 'feature':
            await msgChannel.send(
                "Want to suggest something? Use the template below, otherwise the bot will **NOT** pick it up and do "
                "**NOT** change the first line, it needs to start with ``**Feature Request:**``.\n\nKeep the title "
                "short and to the point.\n```**Feature Request:** Your request\n\n**Extra Information**\n**Who would "
                "use it?**\n**How would it work?**\n**Why should this be added?** Justify why you think it'd help "
                "others```")
        await ctx.send(
            f"Created (or added) {channel.mention} as Listening Channel\nCreated (or added) {tracker.mention} as Tracking Channel.\nIt is using {identifier} as Identifier.")

    @issue.command(name='trackers')
    @commands.guild_only()
    async def trackers(self, ctx):
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        server = Server.from_data(server)
        channels = "You have the following channels setup:\n\n"
        for listen in server.listen:
            channels += f"Listening to: {self.bot.get_channel(listen.channel).mention}\n" \
                        f"Posting to: {self.bot.get_channel(listen.tracker).mention}\n" \
                        f"Using Identifier: ``{listen.identifier}``\n\n"
        await ctx.send(channels)


def setup(bot):
    log.info("[Cogs] Tracker...")
    bot.add_cog(Tracker(bot))
