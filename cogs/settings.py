from discord.ext import commands
from crawler_utilities.events.settings import loopThroughIssueSettings, getIssueSettingsEmbed, getIssueSettingsButtons
from utils import checks

from utils import globals as GG
log = GG.log


class GithubSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            await ctx.send(embed=embed, view=buttons)


def setup(bot):
    log.info("[Cogs] Settings...")
    bot.add_cog(GithubSettings(bot))
