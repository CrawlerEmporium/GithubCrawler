from discord.ext import commands

import utils.globals as GG
from utils import logger
from utils import checks
from utils.functions import get_positivity

log = logger.logger


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def prefix(self, ctx, prefix: str = None):
        """Sets the bot's prefix for this server.

        You must have Manage Server permissions or a role called "Bot Admin" to use this command.

        Forgot the prefix? Reset it with "@IssueCrawler#1030 prefix !".
        """
        guild_id = str(ctx.guild.id)
        if prefix is None:
            current_prefix = await self.bot.get_server_prefix(ctx.message)
            return await ctx.send(f"My current prefix is: `{current_prefix}`")

        self.bot.prefixes[guild_id] = prefix

        await GG.MDB.prefixes.update_one(
            {"guild_id": guild_id},
            {"$set": {"prefix": prefix}},
            upsert=True
        )

        await ctx.send("Prefix set to `{}` for this server.".format(prefix))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def settings(self, ctx, *args):
        """Changes settings for the lookup module.
        __Valid Settings__
        -allow_selfClose [True/False] - Allow people to close their own requests/bugs.
        -allow_milestoneAdding [True/False] - Allow people to add requests/bugs directly to milestones.
        """
        guild_id = str(ctx.guild.id)
        guild_settings = await self.bot.mdb.issuesettings.find_one({"server": guild_id})
        if guild_settings is None:
            guild_settings = {}
        out = ""
        if '-allow_selfClose' in args:
            try:
                setting = args[args.index('-allow_selfClose') + 1]
            except IndexError:
                setting = 'True'
            setting = get_positivity(setting)
            guild_settings['allow_selfClose'] = setting if setting is not None else True
            out += 'allow_selfClose set to {}!\n\n'.format(str(guild_settings['allow_selfClose']))
        if '-allow_milestoneAdding' in args:
            try:
                setting = args[args.index('-allow_milestoneAdding') + 1]
            except IndexError:
                setting = 'True'
            setting = get_positivity(setting)
            guild_settings['allow_milestoneAdding'] = setting if setting is not None else True
            out += 'allow_milestoneAdding set to {}!\n\n'.format(str(guild_settings['allow_milestoneAdding']))

        if guild_settings:
            await self.bot.mdb.issuesettings.update_one({"server": guild_id}, {"$set": guild_settings}, upsert=True)
            out += 'Current Settings for this server:\n'
            out += 'Allow people to close their own requests/bugs: {}\n'.format(str(guild_settings.get('allow_selfClose', 'False')))
            out += 'Allow people to add requests/bugs directly to milestones: {}\n'.format(str(guild_settings.get('allow_milestoneAdding', 'False')))
            await ctx.send("Settings for this server are:\n" + out)
        else:
            await ctx.send("No settings found. Make sure your syntax is correct.")
            await ctx.send(
                "> __Valid Settings__\n"
                "> **-allow_selfClose [True/False]** - Allow people to close their own requests/bugs.\n"
                "> **-allow_milestoneAdding [True/False]** - Allow people to add requests/bugs directly to milestones.")


def setup(bot):
    log.info("[Cogs] Settings...")
    bot.add_cog(Settings(bot))
