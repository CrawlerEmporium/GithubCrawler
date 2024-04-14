import random
from itertools import zip_longest

import discord

from crawler_utilities.handlers.errors import NoSelectionElements
from models.server import Server
from models.githubClient import GitHubClient

from utils import globals as GG
log = GG.log


def discord_trim(string):
    result = []
    trimLen = 0
    lastLen = 0
    while trimLen <= len(string):
        trimLen += 1999
        result.append(string[lastLen:trimLen])
        lastLen += 1999
    return result


async def loadGithubServers():
    log.info("Reloading servers and listeners...")
    orgs = []
    GG.GITHUBSERVERS = []
    GG.ADMINS = []
    GG.SERVERS = []
    GG.BUG_LISTEN_CHANS = []
    servers = await GG.MDB.Github.find({}).to_list(length=None)
    for server in servers:
        newServer = Server.from_data(server)
        GG.GITHUBSERVERS.append(newServer)
        GG.ADMINS.append(newServer.admin)
        GG.SERVERS.append(newServer.server)
    for server in GG.GITHUBSERVERS:
        orgs.append(server.org)
        for channel in server.listen:
            add = {"channel": channel.channel, "tracker": channel.tracker,
                   "identifier": channel.identifier, "type": channel.type, "repo": channel.repo, "url": channel.url}
            GG.BUG_LISTEN_CHANS.append(add)
    GitHubClient.initialize(GG.GITHUB_TOKEN, orgs)


async def get_settings(bot, guildId):
    settings = {}  # default PM settings
    if guildId is not None:
        settings = await bot.mdb.issuesettings.find_one({"server": str(guildId)})
    return settings or {}
