import discord
from utils import globals as GG


async def get_server_feature_identifiers(ctx: discord.AutocompleteContext):
    server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
    identifiers = []
    for identifier in server['listen']:
        if identifier['type'] == "feature":
            identifiers.append(identifier['identifier'])
    return identifiers


async def get_server_bug_identifiers(ctx: discord.AutocompleteContext):
    server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
    identifiers = []
    for identifier in server['listen']:
        if identifier['type'] == "bug":
            identifiers.append(identifier['identifier'])
    return identifiers


async def get_server_identifiers(ctx: discord.AutocompleteContext):
    server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
    identifiers = []
    for identifier in server['listen']:
        identifiers.append(identifier['identifier'])
    return identifiers


async def get_server_reports(ctx: discord.AutocompleteContext):
    if not GG.cachedTrackerChannels:
        guild = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        trackerChannels = []
        for channel in guild['listen']:
            trackerChannels.append(channel['tracker'])
        GG.cachedTrackerChannels.append({"guild_id": ctx.interaction.guild_id, "channels": trackerChannels})
    cachedTrackers = next(server["channels"] for server in GG.cachedTrackerChannels if server['guild_id'] == ctx.interaction.guild_id)
    reports = await GG.MDB.Reports.find({"trackerId": {"$in": cachedTrackers}}).to_list(length=None)
    stringReports = []
    for report in reports:
        stringReports.append({"id": report['report_id'], "title": f"{report['report_id']} | {report['title'][:85]}"})

    if stringReports is not None:
        return [f"{report['id']}" for report in reports if ctx.value.upper() in report['title'].upper()]
    return []
