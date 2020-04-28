import random
import time

import discord
from discord.ext import commands
from environs import Env
from discord import VerificationLevel as VL
from discord import VoiceRegion as VR

from DBService import DBService
import motor.motor_asyncio

env = Env()
env.read_env()

PREFIX = env('PREFIX')
TOKEN = env('TOKEN')
COGS = env('COGS')
OWNER = int(env('OWNER'))
GIDDY = int(env('GIDDY'))
MPMB = int(env('MPMB'))

GUILD = int(env('GUILD'))
CRAWLER = int(env('CRAWLER'))
MPMBS = int(env('MPMBS'))

GITHUB_TOKEN = env('GITHUB_TOKEN')
GITHUB_REPO = env('GITHUB_REPO')

BOT = 574554734187380756
PM_TRUE = True
PREFIXESDB = DBService.exec("SELECT Guild, Prefix FROM Prefixes").fetchall()


def loadChannels(PREFIXESDB):
    prefixes = {}
    for i in PREFIXESDB:
        prefixes[str(i[0])] = str(i[1])
    return prefixes


PREFIXES = loadChannels(PREFIXESDB)


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
        "id": 647162018956181519,
        "identifier": "PLUT",
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
    return ['MPMB','5eTools','Crawlers','Unknown']

MDB = motor.motor_asyncio.AsyncIOMotorClient(env('MONGODB'))['issuetracking']

REPO_ID_MAP = {
    "CrawlerEmporium/5eCrawler": "BUG",
    "CrawlerEmporium/PokemonCrawler":"PBUG",
    "CrawlerEmporium/DiscordCrawler":"DBUG",
    "CrawlerEmporium/GithubCrawler":"GBUG",
    "flapkan/mpmb-tracker": "MBUG",
    "5etools/tracker": "5ET"
}

REACTIONS = [
    "\U0001f640",  # scream_cat
    "\U0001f426",  # bird
    "\U0001f3f9",  # bow_and_arrow
    "\U0001f989",  # owl
    "\U0001f50d",  # mag
    "\U0001f576",  # sunglasses
    "\U0001f575",  # spy
    "\U0001f4e9",  # envelope_with_arrow
    "\U0001f933",  # selfie
    "\U0001f916",  # robot
    "\U0001f409",  # dragon
]

TRACKER_CHAN_5ET = 593769144969723914
TRACKER_CHAN_MPMB = 631432292245569536
TRACKER_CHAN_MPMB_BUG = 704677726287691786
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


def get_server_prefix(self, msg):
    return self.get_prefix(self, msg)[-1]

def countChannels(channels):
    channelCount = 0
    voiceCount = 0
    for x in channels:
        if type(x) is discord.TextChannel:
            channelCount += 1
        elif type(x) is discord.VoiceChannel:
            voiceCount += 1
        else:
            pass
    return channelCount, voiceCount

VERIFLEVELS = {VL.none: "None", VL.low: "Low", VL.medium: "Medium", VL.high: "(╯°□°）╯︵  ┻━┻",
               VL.extreme: "┻━┻ミヽ(ಠ益ಠ)ノ彡┻━┻"}
REGION = {VR.brazil: ":flag_br: Brazil",
          VR.eu_central: ":flag_eu: Central Europe",
          VR.singapore: ":flag_sg: Singapore",
          VR.us_central: ":flag_us: U.S. Central",
          VR.sydney: ":flag_au: Sydney",
          VR.us_east: ":flag_us: U.S. East",
          VR.us_south: ":flag_us: U.S. South",
          VR.us_west: ":flag_us: U.S. West",
          VR.eu_west: ":flag_eu: Western Europe",
          VR.vip_us_east: ":flag_us: VIP U.S. East",
          VR.vip_us_west: ":flag_us: VIP U.S. West",
          VR.vip_amsterdam: ":flag_nl: VIP Amsterdam",
          VR.london: ":flag_gb: London",
          VR.amsterdam: ":flag_nl: Amsterdam",
          VR.frankfurt: ":flag_de: Frankfurt",
          VR.hongkong: ":flag_hk: Hong Kong",
          VR.russia: ":flag_ru: Russia",
          VR.japan: ":flag_jp: Japan",
          VR.southafrica: ":flag_za:  South Africa"}

def checkDays(date):
    now = date.fromtimestamp(time.time())
    diff = now - date
    days = diff.days
    return f"{days} {'day' if days == 1 else 'days'} ago"


class EmbedWithAuthor(discord.Embed):
    """An embed with author image and nickname set."""

    def __init__(self, ctx, **kwargs):
        super(EmbedWithAuthor, self).__init__(**kwargs)
        self.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        self.colour = random.randint(0, 0xffffff)