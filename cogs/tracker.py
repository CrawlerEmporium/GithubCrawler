import typing

import discord
from discord.ext import commands

import utils.globals as GG
from models.server import Server, Listen
from utils import logger
from utils.functions import loadGithubServers, get_selection
from utils.libs.reports import Report

log = logger.logger

TYPES = ['bug', 'feature']


async def findInReports(db, identifier, searchTerm):
    results = []
    list = await db.find({"$text": {"$search": f"\"{searchTerm}\"", "$caseSensitive": False}}).to_list(length=None)
    for x in list:
        if identifier.upper() in x['report_id']:
            results.append(x)
    return results


class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def issue(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```{prefix}issue\n"
                       f"{prefix}issue register\n"
                       f"{prefix}issue channel <type> <identifier> [tracker=0] [channel=0]\n"
                       f"{prefix}issue trackers\n"
                       f"{prefix}issue intro <type>\n"
                       f"{prefix}issue search <identifier> <keyword(s)>\n"
                       f"{prefix}issue searchAll <identifier> <keyword(s)>\n"
                       f"{prefix}issue remove <identifier>\n"
                       f"{prefix}issue manager```")

    @issue.command(name='register')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def issueRegister(self, ctx):
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
    async def issueChannel(self, ctx, type: str, identifier: str, tracker: int = 0, channel: int = 0):
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
        exist = await GG.MDB.ReportNums.find_one({"key": identifier, "server": ctx.guild.id})
        if exist is not None:
            if exist['server'] != ctx.guild.id:
                await ctx.send(
                    "This identifier is already in use, please select another one.")
                return
        await GG.MDB.ReportNums.insert_one({"key": identifier, "server": ctx.guild.id, "amount": 0})


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
            listener = Listen(channel.id, tracker.id, identifier, type, None, "")
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
        try:
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
        except discord.Forbidden:
            await ctx.send(f"Error: I am missing permissions to send the intro message..\n"
                           f"Please make sure I have permission to send messages in <#{msgChannel.id}>.\n\n"
                           f"After granting me permissions, you can run the ``!issue intro bug/feature`` command in that channel, to make me post the intro message.")

        await ctx.send(
            f"Created (or added) {channel.mention} as Listening Channel\nCreated (or added) {tracker.mention} as Tracking Channel.\nIt is using {identifier} as Identifier.")

    @issue.command(name='intro')
    @commands.guild_only()
    async def issueIntro(self, ctx, type):
        type = type.lower()
        if type == 'bug':
            await ctx.send(
                "If you have a bug, you can use the below posted template. Otherwise the bot will **NOT** pick it "
                "up.\n\n```**What is the bug?**: A quick description of the bug.\n\n**Severity**: Trivial (typos, "
                "etc) / Low (formatting issues, things that don't impact operation) / Medium (minor functional "
                "impact) / High (a broken feature, major functional impact) / Critical (bot crash, extremely major "
                "functional impact)\n\n**Steps to reproduce**: How the bug occured, and how to reproduce it. I cannot "
                "bugfix without this.\n\n**Context**: The command run that the bug occured in and any choice "
                "trees.```")
        elif type == 'feature':
            await ctx.send(
                "Want to suggest something? Use the template below, otherwise the bot will **NOT** pick it up and do "
                "**NOT** change the first line, it needs to start with ``**Feature Request:**``.\n\nKeep the title "
                "short and to the point.\n```**Feature Request:** Your request\n\n**Extra Information**\n**Who would "
                "use it?**\n**How would it work?**\n**Why should this be added?** Justify why you think it'd help "
                "others```")
        else:
            await ctx.send("Proper command usage is ``issue intro bug`` or issue intro feature``.")

    @issue.command(name='trackers')
    @commands.guild_only()
    async def issueTrackers(self, ctx):
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        server = Server.from_data(server)
        channels = "You have the following channels setup:\n\n"
        for listen in server.listen:
            channels += f"Listening to: {self.bot.get_channel(listen.channel).mention}\n" \
                        f"Posting to: {self.bot.get_channel(listen.tracker).mention}\n" \
                        f"Using Identifier: ``{listen.identifier}``\n\n"
        await ctx.send(channels)

    @issue.command(name='remove')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def issueRemove(self, ctx, identifier):
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        check = await GG.MDB.ReportNums.find_one({"key": identifier.upper(), "server": ctx.guild.id})

        if check is not None:
            oldListen = []
            for x in server['listen']:
                if x['identifier'] != identifier.upper():
                    oldListen.append(x)
                else:
                    ch = self.bot.get_channel(x['channel'])
                    tr = self.bot.get_channel(x['tracker'])
            server['listen'] = oldListen
            await GG.MDB.Github.replace_one({"server": ctx.guild.id}, server)
            await GG.MDB.ReportNums.delete_one({"key": identifier.upper(), "server": ctx.guild.id})
            if ch is not None and tr is not None:
                await ctx.send(
                    f"``{identifier}`` removed from the database.\n\nYou can now safely remove these channels:\nListener: {ch.mention}, Tracker: {tr.mention}.\n"
                    f"**WARNING**: Deleting these channels could cause the bot to malfunction if you still have other Identifiers linked to these channels. \n"
                    f"Be **VERY** careful before deleting these channels and triple-check before doing so...")
            elif ch is not None:
                await ctx.send(
                    f"``{identifier}`` removed from the database.\nIt's connected listing channel was not found.")
            elif tr is not None:
                await ctx.send(
                    f"``{identifier}`` removed from the database.\nIt's connected tracking channel was not found.")
            else:
                await ctx.send(f"``{identifier}`` removed from the database.\nIt's connected channels were not found.")
        else:
            await ctx.send(f"``{identifier}`` not found...")

    @issue.command(name='search')
    @commands.guild_only()
    async def issueSearch(self, ctx, identifier, *, keywords):
        allReports = await findInReports(GG.MDB.Reports, identifier, keywords)
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for x in server['listen']:
            trackers.append(x['tracker'])
        results = []
        for report in allReports:
            if report['trackerId'] in trackers and report['severity'] != -1:
                results.append(report)
        if len(results) > 0:
            results = [(f"{r['report_id']} - {r['title']}", r) for r in results]
            selection = await get_selection(ctx, results, force_select=True)
            if selection is not None:
                report = await Report.from_id(selection['report_id'])
                if report is not None:
                    await ctx.send(embed=report.get_embed(True, ctx))
                else:
                    await ctx.send("Selected report not found.")
            else:
                return
        else:
            await ctx.send("No results found, please try with a different keyword.")

    @issue.command(name='searchAll')
    @commands.guild_only()
    async def issueSearchAll(self, ctx, identifier, *, keywords):
        allReports = await findInReports(GG.MDB.Reports, identifier, keywords)
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        trackers = []
        for x in server['listen']:
            trackers.append(x['tracker'])
        results = []
        for report in allReports:
            if report['trackerId'] in trackers:
                results.append(report)
        if len(results) > 0:
            results = [(f"{r['report_id']} - {r['title']}", r) for r in results]
            selection = await get_selection(ctx, results, force_select=True)
            if selection is not None:
                report = await Report.from_id(selection['report_id'])
                if report is not None:
                    await ctx.send(embed=report.get_embed(True, ctx))
                else:
                    await ctx.send("Selected report not found.")
            else:
                return
        else:
            await ctx.send("No results found, please try with a different keyword.")

    @issue.group(invoke_without_command=True)
    @commands.guild_only()
    async def manager(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```{prefix}issue manager\n"
                       f"{prefix}issue manager add [member]\n"
                       f"{prefix}issue manager remove [member]\n"
                       f"{prefix}issue manager list```")

    @manager.command(name='add')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def managerAdd(self, ctx, member: typing.Optional[discord.Member]):
        if member is None:
            await ctx.send("Invalid member, please check the name/id and try again.")
            return

        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is not None:
            await ctx.send("Manager already found in the database.")
            return

        await GG.MDB.Managers.insert_one({"user": member.id, "server": ctx.guild.id})
        await ctx.send(f"{member.mention} was added as an issue manager.")

    @manager.command(name='remove')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def managerRemove(self, ctx, member: typing.Optional[discord.Member]):
        if member is None:
            await ctx.send("Invalid member, please check the name/id and try again.")

        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is None:
            await ctx.send("Manager not found in the database, please check the name/id and try again.")

        await GG.MDB.Managers.delete_one({"user": member.id, "server": ctx.guild.id})
        await ctx.send(f"{member.mention} was removed as an issue manager.")

    @manager.command(name='list')
    @commands.guild_only()
    async def managerList(self, ctx):
        server = await GG.MDB.Managers.find({"server": ctx.guild.id}).to_list(length=None)
        if server is None or len(server) <= 0:
            await ctx.send("This server has no managers (Except the Server Owner).")
        else:
            channels = "This server has the following managers:\n\n"
            for x in server:
                user = await ctx.guild.fetch_member(x['user'])
                if user is None:
                    channels += f"{x['user']}\n"
                else:
                    channels += f"{user.mention}\n"
            await ctx.send(channels)


def setup(bot):
    log.info("[Cogs] Tracker...")
    bot.add_cog(Tracker(bot))
