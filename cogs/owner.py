import os
from discord.ext import commands

import utils.globals as GG
from utils import logger

log = logger.logger

extensions = [x.replace('.py', '') for x in os.listdir(GG.COGS) if x.endswith('.py')]

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, extension_name: str):
        """[OWNER ONLY]"""
        try:
            ctx.bot.load_extension(GG.COGS + "." + extension_name)
        except (AttributeError, ImportError) as e:
            await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
            return
        await ctx.send("{} loaded".format(extension_name))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, extension_name: str):
        """[OWNER ONLY]"""
        ctx.bot.unload_extension(GG.COGS + "." + extension_name)
        await ctx.send("{} unloaded".format(extension_name))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, extension_name: str):
        """[OWNER ONLY]"""
        ctx.bot.unload_extension(GG.COGS + "." + extension_name)
        try:
            ctx.bot.load_extension(GG.COGS + "." + extension_name)
        except (AttributeError, ImportError) as e:
            return await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
        await ctx.send("{} reloaded".format(extension_name))


def setup(bot):
    log.info("[Cogs] Owner...")
    bot.add_cog(Owner(bot))
