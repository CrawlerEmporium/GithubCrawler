import typing

import discord
from discord import SlashCommandGroup, Option, AllowedMentions
from discord.ext import commands

from utils import globals as GG

log = GG.log

TYPES = ['bug', 'feature']


class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    manager = SlashCommandGroup("manager", "All commands that have effect on managers for your server",
                                checks=[commands.guild_only().predicate])

    @manager.command(name='add')
    @discord.default_permissions(
        administrator=True,
    )
    async def managerAdd(self, ctx, member: Option(discord.Member, description="Who do you want to add as a manager?")):
        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is not None:
            await ctx.respond("Manager already found in the database.")
            return

        await GG.MDB.Managers.insert_one({"user": member.id, "server": ctx.guild.id})
        await ctx.respond(f"{member.mention} was added as an issue manager.")

    @manager.command(name='remove')
    @discord.default_permissions(
        administrator=True,
    )
    async def managerRemove(self, ctx, member: Option(discord.Member, description="Who do you want to remove as a manager?")):
        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is None:
            await ctx.respond("Manager not found in the database, please check the name/id and try again.")

        await GG.MDB.Managers.delete_one({"user": member.id, "server": ctx.guild.id})
        await ctx.respond(f"{member.mention} was removed as an issue manager.")

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
            await ctx.respond(channels, allowed_mention=AllowedMentions().none())


def setup(bot):
    log.info("[Cogs] Manager...")
    bot.add_cog(Manager(bot))
