import discord
from utils import globals as GG


async def get_server_feature_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.FEATURES)


async def get_server_bug_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.BUGS)


async def get_server_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.IDENTIFIERS)


async def get_identifiers(ctx, lookup):
    identifiers = list(filter(lambda item: item["server"] == ctx.interaction.guild_id, lookup))
    autoList = []
    for identifier in identifiers:
        if identifier["alias"] is not None and identifier["alias"] != "":
            autoList.append(identifier['alias'])
        else:
            autoList.append(identifier['identifier'])
    return autoList


async def get_server_reports(ctx: discord.AutocompleteContext):
    if not GG.cachedTrackerChannels:
        guild = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        trackerChannels = []
        for channel in guild['listen']:
            trackerChannels.append(channel['tracker'])
        GG.cachedTrackerChannels.append({"guild_id": ctx.interaction.guild_id, "channels": trackerChannels})
    cachedTrackers = next(server["channels"] for server in GG.cachedTrackerChannels if server['guild_id'] == ctx.interaction.guild_id)
    if ctx.value == "" or ctx.value is None:
        reports = await GG.MDB.Reports.find({"trackerId": {"$in": cachedTrackers}}).to_list(length=20)
    else:
        reports = await GG.MDB.Reports.find({"trackerId": {"$in": cachedTrackers}}).to_list(length=None)
    if reports is not None:
        reportList = [f"{report['report_id']} | {report['title'][:85] + '...' if report is not None and len(report['title']) >= 90 else report['title']}" for report in reports if ctx.value.upper() in report['report_id']]
        return reportList[0:20]
    return []
