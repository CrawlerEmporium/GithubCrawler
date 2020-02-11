import asyncio
import traceback

import discord
from aiohttp import ClientResponseError, ClientOSError
from discord import Forbidden, HTTPException, InvalidArgument, NotFound
import utils.globals as GG
from errors import CrawlerException, InvalidArgument, EvaluationError
from models.github import Github

from utils import logger
from os import listdir
from os.path import isfile, join
from discord.ext.commands import CommandInvokeError
from discord.ext import commands
from utils.functions import gen_error_message, discord_trim
from utils.libs.github import GitHubClient
from utils.libs.reports import ReportException

log = logger.logger

version = "v1.1.0"
SHARD_COUNT = 1
TESTING = True
defaultPrefix = GG.PREFIX if not TESTING else '*'


class Crawler(commands.AutoShardedBot):
    def __init__(self, prefix, help_command=None, description=None, **options):
        super(Crawler, self).__init__(prefix, help_command, description, **options)
        self.version = version
        self.owner = None
        self.testing = TESTING
        self.token = GG.TOKEN

    async def launch_shards(self):
        if self.shard_count is None:
            recommended_shards, _ = await self.http.get_bot_gateway()
            if recommended_shards >= 96 and not recommended_shards % 16:
                # half, round up to nearest 16
                self.shard_count = recommended_shards // 2 + (16 - (recommended_shards // 2) % 16)
            else:
                self.shard_count = recommended_shards // 2
        log.info(f"Launching {self.shard_count} shards!")
        await super(Crawler, self).launch_shards()


bot = Crawler(prefix=defaultPrefix, case_insensitive=True, status=discord.Status.idle,
              description="A bot.", shard_count=SHARD_COUNT, testing=TESTING,
              activity=discord.Game(f"{defaultPrefix}github | {version}"),
              help_command=commands.DefaultHelpCommand(command_attrs={"name": "github"}))


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(f"with Github | {defaultPrefix}github | {version}"), afk=True)
    print(f"Logged in as {bot.user.name} ({bot.user.id})")


@bot.event
async def on_connect():
    bot.owner = await bot.fetch_user(GG.OWNER)
    orgs = []
    for server in await GG.MDB.Github.find({}).to_list(length=None):
        GG.GITHUBSERVERS.append(Github.from_data(server))
    for server in GG.GITHUBSERVERS:
        orgs.append(server.org)
        for channel in server.listen:
            add = {"id": channel.id, "identifier": channel.identifier, "repo": channel.repo}
            GG.BUG_LISTEN_CHANS.append(add)
    GitHubClient.initialize(GG.GITHUB_TOKEN, orgs)


@bot.event
async def on_resumed():
    log.info('resumed.')


@bot.event
async def on_guild_join(guild):
    bots = sum(1 for m in guild.members if m.bot)
    members = len(guild.members)
    ratio = bots / members
    if ratio >= 0.6 and members >= 20:
        log.info("Detected bot collection server ({}), ratio {}. Leaving.".format(guild.id, ratio))
        try:
            await guild.owner.send("Please do not add me to bot collection servers. "
                                   "Your server was flagged for having over 60% bots. "
                                   "If you believe this is an error, please PM the bot author.")
        except:
            pass
        await asyncio.sleep(members / 200)
        await guild.leave()
    else:
        await bot.change_presence(activity=discord.Game(f"with Github | {defaultPrefix}github | {version}"),
                                  afk=True)


@bot.event
async def on_command_error(ctx, error):
    owner = bot.get_user(GG.OWNER)
    if isinstance(error, commands.CommandNotFound):
        return
    log.debug("Error caused by message: `{}`".format(ctx.message.content))
    log.debug('\n'.join(traceback.format_exception(type(error), error, error.__traceback__)))
    if isinstance(error, CrawlerException):
        return await ctx.send(str(error))
    tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    if isinstance(error,
                  (commands.MissingRequiredArgument, commands.BadArgument, commands.NoPrivateMessage, ValueError)):
        return await ctx.send("Error: " + str(
            error) + f"\nUse `{defaultPrefix}help " + ctx.command.qualified_name + "` for help.")
    elif isinstance(error, commands.CheckFailure):
        return await ctx.send("Error: You are not allowed to run this command.")
    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send("This command is on cooldown for {:.1f} seconds.".format(error.retry_after))
    elif isinstance(error, CommandInvokeError):
        original = error.original
        if isinstance(original, EvaluationError):  # PM an alias author tiny traceback
            e = original.original
            if not isinstance(e, CrawlerException):
                tb = f"```py\nError when parsing expression {original.expression}:\n" \
                     f"{''.join(traceback.format_exception(type(e), e, e.__traceback__, limit=0, chain=False))}\n```"
                try:
                    await ctx.author.send(tb)
                except Exception as e:
                    log.info(f"Error sending traceback: {e}")
        if isinstance(original, CrawlerException):
            return await ctx.send(str(original))
        if isinstance(original, ReportException):
            return await ctx.send(str(original))
        if isinstance(original, Forbidden):
            try:
                return await ctx.author.send(
                    f"Error: I am missing permissions to run this command. "
                    f"Please make sure I have permission to send messages to <#{ctx.channel.id}>."
                )
            except:
                try:
                    return await ctx.send(f"Error: I cannot send messages to this user.")
                except:
                    return
        if isinstance(original, NotFound):
            return await ctx.send("Error: I tried to edit or delete a message that no longer exists.")
        if isinstance(original, ValueError) and str(original) in ("No closing quotation", "No escaped character"):
            return await ctx.send("Error: No closing quotation.")
        if isinstance(original, (ClientResponseError, InvalidArgument, asyncio.TimeoutError, ClientOSError)):
            return await ctx.send("Error in Discord API. Please try again.")
        if isinstance(original, HTTPException):
            if original.response.status == 400:
                return await ctx.send("Error: Message is too long, malformed, or empty.")
            if original.response.status == 500:
                return await ctx.send("Error: Internal server error on Discord's end. Please try again.")
        if isinstance(original, OverflowError):
            return await ctx.send(f"Error: A number is too large for me to store.")

    error_msg = gen_error_message()

    await ctx.send(
        f"Error: {str(error)}\nUh oh, that wasn't supposed to happen! "
        f"Please join the Support Discord and tell the developer that: **{error_msg}!**")
    try:
        await owner.send(
            f"**{error_msg}**\n" \
            + "Error in channel {} ({}), server {} ({}): {}\nCaused by message: `{}`".format(
                ctx.channel, ctx.channel.id, ctx.guild,
                ctx.guild.id, repr(error),
                ctx.message.content))
    except AttributeError:
        await owner.send(f"**{error_msg}**\n" \
                         + "Error in PM with {} ({}), shard 0: {}\nCaused by message: `{}`".format(
            ctx.author.mention, str(ctx.author), repr(error), ctx.message.content))
    for o in discord_trim(tb):
        await owner.send(o)
    log.error("Error caused by message: `{}`".format(ctx.message.content))


if __name__ == "__main__":
    bot.state = "run"
    for extension in [f.replace('.py', '') for f in listdir(GG.COGS) if isfile(join(GG.COGS, f))]:
        try:
            bot.load_extension(GG.COGS + "." + extension)
        except Exception as e:
            log.error(f'Failed to load extension {extension}')
    bot.run(bot.token)
