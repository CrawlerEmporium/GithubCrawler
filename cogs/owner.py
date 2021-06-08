import asyncio
import os
import subprocess
import inspect

from discord.ext.commands import BucketType

import utils.globals as GG
from discord.ext import commands

from utils import logger

log = logger.logger


extensions = [x.replace('.py', '') for x in os.listdir(GG.COGS) if x.endswith('.py')]
path = GG.COGS + '.'

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def gitpull(self, ctx):
        """Pulls from github and updates bot"""
        await ctx.trigger_typing()
        await ctx.send(f"```{subprocess.run('git pull', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')}```")
        for cog in extensions:
            ctx.bot.unload_extension(f'{path}{cog}')
        for cog in extensions:
            members = inspect.getmembers(cog)
            for name, member in members:
                if name.startswith('on_'):
                    ctx.bot.add_listener(member, name)
            try:
                ctx.bot.load_extension(f'{path}{cog}')
            except Exception as e:
                await ctx.send(f'LoadError: {cog}\n{type(e).__name__}: {e}')
        await ctx.send('All cogs reloaded :white_check_mark:')

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

    @commands.command(hidden=True)
    @commands.is_owner()
    @commands.max_concurrency(1, BucketType.user)
    async def multiline(self, ctx, *, cmds: str):
        """Runs each line as a separate command, with a 1 second delay between commands.
        Limited to 1 multiline every 20 seconds, with a max of 20 commands, due to abuse.
        Usage:
        "!multiline
        !command1
        !command2
        !command3"
        """
        cmds = cmds.splitlines()
        for c in cmds[:20]:
            ctx.message.content = c
            await self.bot.process_commands(ctx.message)
            await asyncio.sleep(1)


def setup(bot):
    log.info("[Cogs] Owner...")
    bot.add_cog(Owner(bot))
