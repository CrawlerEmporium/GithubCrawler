import asyncio

import discord
import utils.globals as GG

from utils import logger
from os import listdir
from os.path import isfile, join
from discord.ext import commands

from utils.functions import loadGithubServers

log = logger.logger

version = "v1.1.0"
SHARD_COUNT = 1
TESTING = False
defaultPrefix = GG.PREFIX if not TESTING else '&'


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
    await loadGithubServers()
    await bot.change_presence(activity=discord.Game(f"with Github | {defaultPrefix}github | {version}"), afk=True)
    print(f"Logged in as {bot.user.name} ({bot.user.id})")


@bot.event
async def on_connect():
    bot.owner = await bot.fetch_user(GG.OWNER)


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


if __name__ == "__main__":
    bot.state = "run"
    log.info("Loading Cogs...")
    for extension in [f.replace('.py', '') for f in listdir(GG.COGS) if isfile(join(GG.COGS, f))]:
        try:
            bot.load_extension(GG.COGS + "." + extension)
        except Exception as e:
            log.error(f'Failed to load extension {extension}')
    log.info("-------------------")
    log.info("Loading Event Cogs...")
    for extension in [f.replace('.py', '') for f in listdir("cogsEvents") if isfile(join("cogsEvents", f))]:
        try:
            bot.load_extension("cogsEvents" + "." + extension)
        except Exception as e:
            log.error(f'Failed to load extension {extension}')
    log.info("-------------------")
    log.info("Finished Loading All Cogs...")
    bot.run(bot.token)
