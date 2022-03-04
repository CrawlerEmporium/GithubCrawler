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
