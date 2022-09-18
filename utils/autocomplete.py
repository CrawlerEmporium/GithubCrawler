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


async def get_server_identifiers_no_alias(ctx: discord.AutocompleteContext):
    return await get_identifiers(ctx, GG.ALL_IDENTIFIERS, False)


async def get_identifiers(ctx, lookup, alias=True):
    identifiers = list(filter(lambda item: item["server"] == ctx.interaction.guild_id, lookup))
    autoList = []
    for identifier in identifiers:
        if alias:
            if identifier["alias"] is not None and identifier["alias"] != "":
                autoList.append(identifier['alias'])
            else:
                autoList.append(identifier['identifier'])
        else:
            autoList.append(identifier['identifier'])
    return autoList


async def get_server_tickets(ctx: discord.AutocompleteContext):
    autoList = []
    tickets = []
    servers = list(filter(lambda item: item['guild_id'] == ctx.interaction.guild_id, GG.TRACKING_CHANNELS))
    for server in servers:
        tickets += server['tickets']
    for ticket in tickets:
        if len(autoList) < 25:
            if ticket is not None:
                if ctx.value.upper() in ticket['ticket_id']:
                    autoList.append(f"{ticket['ticket_id']} | {ticket['title'][:85] + '...' if len(ticket['title']) >= 85 else ticket['title']}")
        else:
            return autoList
    return autoList
