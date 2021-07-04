import utils.globals as GG

from discord.ext import commands
from crawler_utilities.events.settings import loopThroughIssueSettings, getIssueSettingsEmbed, getIssueSettingsButtons
from crawler_utilities.handlers import logger
from utils import checks

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

        loopedSettings = loopThroughIssueSettings(guild_settings, args)

        out = ""
        if '-allow_selfClose' in args:
            out += 'allow_selfClose set to {}!\n\n'.format(str(loopedSettings['allow_selfClose']))
        if '-allow_milestoneAdding' in args:
            out += 'allow_milestoneAdding set to {}!\n\n'.format(str(loopedSettings['allow_milestoneAdding']))

        if bool(loopedSettings):
            await self.bot.mdb.issuesettings.update_one({"server": guild_id}, {"$set": loopedSettings}, upsert=True)

        if len(out) > 0:
            await ctx.send(out)
        else:
            embed = getIssueSettingsEmbed(loopedSettings, ctx.author)
            buttons = getIssueSettingsButtons(loopedSettings)
            await ctx.send(embed=embed, components=buttons)


def setup(bot):
    log.info("[Cogs] Settings...")
    bot.add_cog(Settings(bot))
