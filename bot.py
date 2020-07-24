import asyncio

import discord
import utils.globals as GG

from utils import logger
from os import listdir
from os.path import isfile, join
from discord.ext import commands
from utils.libs.github import GitHubClient
from models.server import Server

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


async def loadGithubServers():
    orgs = []
    GG.GITHUBSERVERS = []
    GG.BUG_LISTEN_CHANS = []
    GG.ADMINS = []
    GG.SERVERS = []
    for server in await GG.MDB.Github.find({}).to_list(length=None):
        newServer = Server.from_data(server)
        GG.GITHUBSERVERS.append(newServer)
        GG.ADMINS.append(newServer.admin)
        GG.SERVERS.append(newServer.server)
    for server in GG.GITHUBSERVERS:
        orgs.append(server.org)
        for channel in server.listen:
            add = {"id": channel.id, "identifier": channel.identifier, "repo": channel.repo}
            GG.BUG_LISTEN_CHANS.append(add)
    GitHubClient.initialize(GG.GITHUB_TOKEN, orgs)


if __name__ == "__main__":
    bot.state = "run"
    bot.loop.create_task(loadGithubServers())
    for extension in [f.replace('.py', '') for f in listdir(GG.COGS) if isfile(join(GG.COGS, f))]:
        try:
            bot.load_extension(GG.COGS + "." + extension)
        except Exception as e:
            log.error(f'Failed to load extension {extension}')

    for extension in [f.replace('.py', '') for f in listdir("cogsEvents") if isfile(join("cogsEvents", f))]:
        try:
            bot.load_extension("cogsEvents" + "." + extension)
        except Exception as e:
            log.error(f'Failed to load extension {extension}')

    bot.run(bot.token)
