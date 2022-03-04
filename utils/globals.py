from discord.ext import commands
from environs import Env
import motor.motor_asyncio

from utils.functions import get_settings

from crawler_utilities.handlers import logger

log = logger.logger

env = Env()
env.read_env()

PREFIX = env('PREFIX')
TOKEN = env('TOKEN')
TEST_TOKEN = env('TEST_TOKEN')
COGS = env('COGS')
OWNER = int(env('OWNER'))

GITHUB_TOKEN = env('GITHUB_TOKEN')
GITHUB_REPO = env('GITHUB_REPO')
MONGODB = env('MONGODB')

BOT = 574554734187380756
PM_TRUE = True

MDB = motor.motor_asyncio.AsyncIOMotorClient(MONGODB)['issuetracking']
HELP = motor.motor_asyncio.AsyncIOMotorClient(MONGODB)['lookup']

GITHUBSERVERS = []
BUG_LISTEN_CHANS = []
ADMINS = []
SERVERS = []

REPO_ID_MAP = {
    "CrawlerEmporium/5eCrawler": "BUG",
    "CrawlerEmporium/PokemonCrawler": "PBUG",
    "CrawlerEmporium/DiscordCrawler": "DBUG",
    "CrawlerEmporium/GithubCrawler": "GBUG",
    "CrawlerEmporium/ScheduleCrawler": "SBUG",
    "CrawlerEmporium/CrawlerEmporium": "WBUG",
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


def checkPermission(ctx, permission):
    if ctx.guild is None:
        return True
    if permission == "mm":
        return ctx.guild.me.guild_permissions.manage_messages
    if permission == "af":
        return ctx.guild.me.guild_permissions.attach_files
    if permission == "ar":
        return ctx.guild.me.guild_permissions.add_reactions
    else:
        return False


class ContextProxy:  # just to pass the bot on to functions that need it
    def __init__(self, bot, **kwargs):
        self.bot = bot
        for k, v in kwargs.items():
            self.__setattr__(k, v)


class FakeAuthor:
    def __init__(self, member):
        self.author = member
