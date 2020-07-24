import random
import discord
from discord.ext import commands
from environs import Env
import motor.motor_asyncio

env = Env()
env.read_env()

PREFIX = env('PREFIX')
TOKEN = env('TOKEN')
COGS = env('COGS')
OWNER = int(env('OWNER'))

GITHUB_TOKEN = env('GITHUB_TOKEN')
GITHUB_REPO = env('GITHUB_REPO')

BOT = 574554734187380756
PM_TRUE = True

MDB = motor.motor_asyncio.AsyncIOMotorClient(env('MONGODB'))['issuetracking']

GITHUBSERVERS = []
BUG_LISTEN_CHANS = []
ADMINS = []
SERVERS = []

REPO_ID_MAP = {
    "CrawlerEmporium/5eCrawler": "BUG",
    "CrawlerEmporium/PokemonCrawler": "PBUG",
    "CrawlerEmporium/DiscordCrawler": "DBUG",
    "CrawlerEmporium/GithubCrawler": "GBUG",
    "flapkan/mpmb-tracker": "MBUG",
    "5etools/tracker": "5ET",
    "FantasyModuleParser/FantasyModuleParser": "FMPBUG"
}

TRACKER_CHAN_5ET = 593769144969723914
TRACKER_CHAN_MPMB = 631432292245569536
TRACKER_CHAN_MPMB_BUG = 704677726287691786
TRACKER_CHAN = 590812637072195587
TRACKER_CHAN_FMP = 733051447582785576


def is_owner():
    async def predicate(ctx):
        if ctx.author.id == OWNER or ctx.author.id == ctx.guild.owner_id:
            return True
        else:
            return False

    return commands.check(predicate)


def is_in_guild(guild_id):
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == guild_id

    return commands.check(predicate)


async def getServerObject(guildID):
    for guild in GITHUBSERVERS:
        if guild.server == guildID:
            return guild
    return None

class EmbedWithAuthor(discord.Embed):
    """An embed with author image and nickname set."""

    def __init__(self, ctx, **kwargs):
        super(EmbedWithAuthor, self).__init__(**kwargs)
        self.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        self.colour = random.randint(0, 0xffffff)
