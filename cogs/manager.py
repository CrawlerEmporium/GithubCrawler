import typing

import discord
from discord.ext import commands

import utils.globals as GG
from crawler_utilities.handlers import logger

log = logger.logger

TYPES = ['bug', 'feature']


class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def manager(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```{prefix}manager\n"
                       f"{prefix}manager add [member]\n"
                       f"{prefix}manager remove [member]\n"
                       f"{prefix}manager list```")

    @manager.command(name='add')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def managerAdd(self, ctx, member: typing.Optional[discord.Member]):
        if member is None:
            await ctx.send("Invalid member, please check the name/id and try again.")
            return

        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is not None:
            await ctx.send("Manager already found in the database.")
            return

        await GG.MDB.Managers.insert_one({"user": member.id, "server": ctx.guild.id})
        await ctx.send(f"{member.mention} was added as an issue manager.")

    @manager.command(name='remove')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def managerRemove(self, ctx, member: typing.Optional[discord.Member]):
        if member is None:
            await ctx.send("Invalid member, please check the name/id and try again.")

        manager = await GG.MDB.Managers.find_one({"user": member.id, "server": ctx.guild.id})
        if manager is None:
            await ctx.send("Manager not found in the database, please check the name/id and try again.")

        await GG.MDB.Managers.delete_one({"user": member.id, "server": ctx.guild.id})
        await ctx.send(f"{member.mention} was removed as an issue manager.")

    @manager.command(name='list')
    @commands.guild_only()
    async def managerList(self, ctx):
        server = await GG.MDB.Managers.find({"server": ctx.guild.id}).to_list(length=None)
        if server is None or len(server) <= 0:
            await ctx.send("This server has no managers (Except the Server Owner).")
        else:
            channels = "This server has the following managers:\n\n"
            for x in server:
                user = await ctx.guild.fetch_member(x['user'])
                if user is None:
                    channels += f"{x['user']}\n"
                else:
                    channels += f"{user.mention}\n"
            await ctx.send(channels)


def setup(bot):
    log.info("[Cogs] Manager...")
    bot.add_cog(Manager(bot))
