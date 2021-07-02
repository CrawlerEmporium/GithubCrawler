import logging
import random
from itertools import zip_longest

import discord

import utils.globals as GG
from crawler_utilities.handlers.errors import NoSelectionElements
from models.server import Server
from crawler_utilities.utils.pagination import BotEmbedPaginator
from models.githubClient import GitHubClient

log = logging.getLogger(__name__)


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


async def get_selection(ctx, choices, delete=True, pm=False, message=None, force_select=False):
    """Returns the selected choice, or None. Choices should be a list of two-tuples of (name, choice).
    If delete is True, will delete the selection message and the response.
    If length of choices is 1, will return the only choice.
    :raises NoSelectionElements if len(choices) is 0.
    :raises SelectionCancelled if selection is cancelled."""
    if len(choices) == 0:
        raise NoSelectionElements()
    elif len(choices) == 1 and not force_select:
        return choices[0][1]

    page = 0
    pages = paginate(choices, 10)
    m = None
    selectMsg = None
    colour = random.randint(0, 0xffffff)
    embeds = []

    # def chk(msg):
    #     valid = [str(v) for v in range(1, len(choices) + 1)]
    #     return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in valid

    for x in range(len(pages)):
        _choices = pages[x]
        names = [o[0] for o in _choices if o]
        embed = discord.Embed()
        embed.title = "Multiple Matches Found"
        selectStr = "Which one were you looking for? (Type the number or press ⏹ to cancel)\n"
        for i, r in enumerate(names):
            selectStr += f"**[{i + 1 + x * 10}]** - {r}\n"
        embed.description = selectStr
        embed.colour = colour
        if message:
            embed.add_field(name="Note", value=message)
        embeds.append(embed)

    if selectMsg:
        try:
            await selectMsg.delete()
        except:
            pass

    valid = [str(v) for v in range(1, len(choices) + 1)]

    paginator = BotEmbedPaginator(ctx, embeds)
    m = await paginator.run(valid=valid)

    if m is not None:
        return choices[int(m) - 1][1]
    else:
        return None


async def get_settings(bot, guildId):
    settings = {}  # default PM settings
    if guildId is not None:
        settings = await bot.mdb.issuesettings.find_one({"server": str(guildId)})
    return settings or {}


def paginate(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return [i for i in zip_longest(*args, fillvalue=fillvalue) if i is not None]
