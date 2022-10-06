import typing

import discord
from discord import SlashCommandGroup, Option, AllowedMentions
from discord.ext import commands

from utils import globals as GG
from utils.autocomplete import get_server_identifiers

log = GG.log


class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    manager = SlashCommandGroup("manager", "All commands that have effect on managers for your server",
                                checks=[commands.guild_only().predicate])

    @manager.command(name='add')
    @discord.default_permissions(
        administrator=True,
    )
    async def managerAdd(self, ctx, member: Option(discord.Member, description="Who do you want to add as a manager?"), identifier: Option(str, "For which identifier? Leave empty for server wide.", default=None, autocomplete=get_server_identifiers, required=False)):
        if identifier is None:
            manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
            if manager is not None:
                return await ctx.respond("Manager already found in the database.")
            await GG.MDB.Managers.insert_one({"user": member.id, "server": ctx.guild.id})
            await ctx.respond(f"{member.mention} was added as an issue manager.")
        else:
            manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id, "identifier": identifier})
            if manager is not None:
                return await ctx.respond(f"Manager already found in the database for {identifier}.")
            await GG.MDB.Managers.insert_one({"user": member.id, "server": ctx.guild.id, "identifier": identifier})
            await ctx.respond(f"{member.mention} was added as an issue manager for {identifier}.")

    @manager.command(name='remove')
    @discord.default_permissions(
        administrator=True,
    )
    async def managerRemove(self, ctx, member: Option(discord.Member, description="Who do you want to remove as a manager?"), identifier: Option(str, "For which identifier? Leave empty for server wide.", default=None, autocomplete=get_server_identifiers, required=False)):
        if identifier is None:
            manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
            if manager is None:
                return await ctx.respond("Manager not found in the database, please check the name/id and try again.")

            await GG.MDB.Managers.delete_one({"user": member.id, "server": ctx.guild.id})
            await ctx.respond(f"{member.mention} was removed as an issue manager.")
        else:
            manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id, "identifier": identifier})
            if manager is None:
                return await ctx.respond(f"Manager not found in the database for {identifier}, please check the name/id and try again.")

            await GG.MDB.Managers.delete_one({"user": member.id, "server": ctx.guild.id, "identifier": identifier})
            await ctx.respond(f"{member.mention} was removed as an issue manager for {identifier}.")

    @manager.command(name='list')
    async def managerList(self, ctx):
        server = await GG.MDB.Managers.find({"server": ctx.guild.id}).to_list(length=None)
        if server is None or len(server) <= 0:
            await ctx.respond("This server has no managers (Except the Server Owner).")
        else:
            channels = "This server has the following managers:\n\n"
            for x in server:
                user = await ctx.guild.fetch_member(x['user'])
                if user is None:
                    channels += f"{x['user']}\n"
                else:
                    channels += f"{user.mention}\n"
            await ctx.respond(channels, allowed_mentions=AllowedMentions().none())


def setup(bot):
    log.info("[Cogs] Manager...")
    bot.add_cog(Manager(bot))
