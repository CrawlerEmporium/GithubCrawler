import discord
from utils import globals as GG


async def get_server_feature_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.FEATURE_IDENTIFIERS)


async def get_server_bug_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.BUG_IDENTIFIERS)


async def get_server_support_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.SUPPORT_IDENTIFIERS)


async def get_server_identifiers(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.ALL_IDENTIFIERS)


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
    autoList = []
    reports = []
    servers = list(filter(lambda item: item['guild_id'] == ctx.interaction.guild_id, GG.TRACKING_CHANNELS))
    for server in servers:
        reports += server['reports']
    for report in reports:
        if report is not None:
            if ctx.value.upper() in report['report_id']:
                autoList.append(f"{report['report_id']} | {report['title'][:85] + '...' if len(report['title']) >= 85 else report['title']}")
    return autoList
