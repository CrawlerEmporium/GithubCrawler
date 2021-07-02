import asyncio
import os
import subprocess
import inspect

from discord.ext.commands import BucketType

import utils.globals as GG
from discord.ext import commands

from crawler_utilities.handlers import logger

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
    async def commands(self, ctx):
        nonHiddenCommands = []
        for command in self.bot.commands:
            if not command.hidden:
                nonHiddenCommands.append(command.qualified_name)
        query = {"bots": "issue", "disabled": None, "command": {"$in": nonHiddenCommands}}

        missingHelpCommands = await GG.HELP['help'].find(query).to_list(length=None)
        for command in missingHelpCommands:
            if command['command'] in nonHiddenCommands:
                nonHiddenCommands.remove(command['command'])

        string = ""
        for command in nonHiddenCommands:
            string += f"{command}\n"
            if len(string) > 1800:
                await ctx.send(string)
                string = ""
        await ctx.send(string)


def setup(bot):
    log.info("[Cogs] Owner...")
    bot.add_cog(Owner(bot))
