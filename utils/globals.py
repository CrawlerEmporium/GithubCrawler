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

GITHUB_TOKEN = env('GITHUB_TOKEN')
GITHUB_REPO = env('GITHUB_REPO')

BOT = 574554734187380756
PM_TRUE = True


OWNER = int(env('OWNER'))
GIDDY = int(env('GIDDY'))
MPMB = int(env('MPMB'))

GUILD = int(env('GUILD'))
CRAWLER = int(env('CRAWLER'))
MPMBS = int(env('MPMBS'))

BUG_LISTEN_CHANS = [
    {
        "id": 590812355504373793,
        "identifier": "BUG",
        "repo": "CrawlerEmporium/5eCrawler"
    },
    {
        "id": 590812381123313664,
        "identifier": "FR",
        "repo": "CrawlerEmporium/5eCrawler"
    },
    {
        "id": 601369635178151978,
        "identifier": "PBUG",
        "repo": "CrawlerEmporium/PokemonCrawler"
    },
    {
        "id": 601369662030217217,
        "identifier": "PFR",
        "repo": "CrawlerEmporium/PokemonCrawler"
    },
    {
        "id": 602780405518827540,
        "identifier": "DBUG",
        "repo": "CrawlerEmporium/DiscordCrawler"
    },
    {
        "id": 602780442147684352,
        "identifier": "DFR",
        "repo": "CrawlerEmporium/DiscordCrawler"
    },
    {
        "id": 602780421847253012,
        "identifier": "GBUG",
        "repo": "CrawlerEmporium/GithubCrawler"
    },
    {
        "id": 602780489287467019,
        "identifier": "GFR",
        "repo": "CrawlerEmporium/GithubCrawler"
    },
    {
        "id": 470673367628906496,
        "identifier": "5ET",
        "repo": "5etools/tracker"
    },
    {
        "id": 594095427314384897,
        "identifier": "R20",
        "repo": "5etools/tracker"
    },
    {
        "id": 554644051098337280,
        "identifier": "MBUG",
        "repo": "flapkan/mpmb-tracker"
    },
    {
        "id": 636149281597685760,
        "identifier": "MFR",
        "repo": "flapkan/mpmb-tracker"
    }
]

MDB = motor.motor_asyncio.AsyncIOMotorClient(env('MONGODB'))['issuetracking']

GITHUB = []

def getServer(repo):
    if repo == "flapkan/mpmb-tracker":
        return "MPMB"
    if repo == "5etools/tracker":
        return "5eTools"
    if repo == "5ecrawler/tracker":
        return "Crawlers"
    if "CrawlerEmporium" in repo:
        return "Crawlers"
    else:
        return "Unknown"


def getAllServers():
    return ['MPMB', '5eTools', 'Crawlers', 'Unknown']

REPO_ID_MAP = {
    "CrawlerEmporium/5eCrawler": "BUG",
    "CrawlerEmporium/PokemonCrawler": "PBUG",
    "CrawlerEmporium/DiscordCrawler": "DBUG",
    "CrawlerEmporium/GithubCrawler": "GBUG",
    "flapkan/mpmb-tracker": "MBUG",
    "5etools/tracker": "5ET"
}

TRACKER_CHAN_5ET = 593769144969723914
TRACKER_CHAN_MPMB = 631432292245569536
TRACKER_CHAN = 590812637072195587

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


class EmbedWithAuthor(discord.Embed):
    """An embed with author image and nickname set."""

    def __init__(self, ctx, **kwargs):
        super(EmbedWithAuthor, self).__init__(**kwargs)
        self.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        self.colour = random.randint(0, 0xffffff)
