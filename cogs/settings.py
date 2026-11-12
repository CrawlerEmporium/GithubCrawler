from discord import Option, slash_command
from discord.ext import commands
from crawler_utilities.events.settings import loopThroughIssueSettings, getIssueSettingsEmbed, getIssueSettingsButtons

from utils import globals as GG
log = GG.log


class GithubSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="settings")
    @commands.guild_only()
    async def settings(
        self,
        ctx,
        allow_self_close: Option(bool, "Allow people to close their own requests/bugs", required=False) = None,
        allow_milestone_adding: Option(bool, "Allow people to add requests/bugs directly to milestones", required=False) = None,
    ):
        """Changes settings for the lookup module.
        """
        is_bot_owner = ctx.author.id == GG.OWNER
        has_manage_guild = ctx.channel.permissions_for(ctx.author).manage_guild
        has_bot_admin_role = any(role.name.lower() == "bot admin" for role in ctx.author.roles)
        if not (is_bot_owner or has_manage_guild or has_bot_admin_role):
            return await ctx.respond(
                "You need the 'Bot Admin' role or Manage Server permission to change settings.",
                ephemeral=True,
            )

        guild_id = str(ctx.guild.id)
        guild_settings = await self.bot.mdb.issuesettings.find_one({"server": guild_id})
        if guild_settings is None:
            guild_settings = {}

        args = []
        if allow_self_close is not None:
            args.extend(("-allow_selfClose", str(allow_self_close)))
        if allow_milestone_adding is not None:
            args.extend(("-allow_milestoneAdding", str(allow_milestone_adding)))
        loopedSettings = loopThroughIssueSettings(guild_settings, args)

        out = ""
        if allow_self_close is not None:
            out += 'allow_selfClose set to {}!\n\n'.format(str(loopedSettings['allow_selfClose']))
        if allow_milestone_adding is not None:
            out += 'allow_milestoneAdding set to {}!\n\n'.format(str(loopedSettings['allow_milestoneAdding']))

        if bool(loopedSettings):
            await self.bot.mdb.issuesettings.update_one({"server": guild_id}, {"$set": loopedSettings}, upsert=True)

        if len(out) > 0:
            await ctx.respond(out)
        else:
            embed = getIssueSettingsEmbed(loopedSettings, ctx.author)
            buttons = getIssueSettingsButtons(loopedSettings)
            await ctx.respond(embed=embed, view=buttons)


def setup(bot):
    log.info("[Cogs] Settings...")
    bot.add_cog(GithubSettings(bot))
