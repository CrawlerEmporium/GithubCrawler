import logging
import random
import re
from itertools import zip_longest

import discord

import utils.globals as GG
from models.server import Server
from disputils import BotEmbedPaginator
from models.errors import NoResultsFound, NoSelectionElements
from utils.libs.github import GitHubClient

log = logging.getLogger(__name__)


class SearchException(Exception):
    pass


def discord_trim(string):
    result = []
    trimLen = 0
    lastLen = 0
    while trimLen <= len(string):
        trimLen += 1999
        result.append(string[lastLen:trimLen])
        lastLen += 1999
    return result


def gen_error_message():
    subject = random.choice(['A kobold', 'The green dragon', 'The Frost Mage', 'GithubCrawler', 'The wizard',
                             'An iron golem', 'Giddy', 'Your mom', 'This bot', 'You', 'Me', 'The president',
                             'The Queen', 'Xanathar', 'Volo', 'This world'])
    verb = random.choice(['must be', 'should be', 'has been', 'will be', 'is being', 'was being'])
    thing_to_do = random.choice(['stopped', 'killed', 'talked to', 'found', 'destroyed', 'fought'])
    return f"{subject} {verb} {thing_to_do}"


def a_or_an(string, upper=False):
    if string.startswith('^') or string.endswith('^'):
        return string.strip('^')
    if re.match('[AEIOUaeiou].*', string):
        return 'an {0}'.format(string) if not upper else f'An {string}'
    return 'a {0}'.format(string) if not upper else f'A {string}'


def camel_to_title(string):
    return re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', string).title()


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

    paginator = BotEmbedPaginator(ctx, embeds)
    m = await paginator.run()

    if m is not None:
        return choices[int(m) - 1][1]
    else:
        return None


def get_positivity(string):
    if isinstance(string, bool):  # oi!
        return string
    lowered = string.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
        return False
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


async def splitDiscordEmbedField(embed, input, embed_field_name):
    texts = []
    while len(input) > 1024:
        next_text = input[:1024]
        last_space = next_text.rfind(" ")
        input = "…" + input[last_space + 1:]
        next_text = next_text[:last_space] + "…"
        texts.append(next_text)
    texts.append(input)
    embed.add_field(name=embed_field_name, value=texts[0], inline=False)
    for piece in texts[1:]:
        embed.add_field(name="** **", value=piece, inline=False)
