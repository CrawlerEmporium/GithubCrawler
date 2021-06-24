from discord.ext import commands
from discord_components import Button, ButtonStyle

import utils.globals as GG
from crawler_utilities.handlers import logger
from utils import checks
from crawler_utilities.utils.embeds import EmbedWithAuthorWithoutContext
from crawler_utilities.utils.functions import get_positivity

log = logger.logger

active = "(<:active:851743586583052329> Active)"
inactive = "(<:inactive:851743586654748672> Inactive)"
settingsTrue = ['-allow_selfClose True', '-allow_milestoneAdding True']
settingsFalse = ['-allow_selfClose False', '-allow_milestoneAdding False']


def getSettingsEmbed(settings, author):
    embed = EmbedWithAuthorWithoutContext(author)
    embed.title = "IssueCrawler settings for this server."

    selfClose = active if settings.get('allow_selfClose', False) else inactive
    milestoneAdding = active if settings.get('allow_milestoneAdding', False) else inactive

    reportString = '🔒 Allow people to close their own requests/bugs: {}\n'.format(str(selfClose))
    milestoneString = '🐛 Allow people to add requests/bugs directly to milestones: {}\n'.format(str(milestoneAdding))

    embed.add_field(name="Report Settings", value=reportString, inline=False)
    embed.add_field(name="Milestone Settings", value=milestoneString, inline=False)

    embed.set_footer(text="Click the buttons below to change the status from active to inactive, or vice versa")

    return embed


def getSettingsButtons(settings):
    close = Button(style=ButtonStyle.green, custom_id="-allow_selfClose False") if settings.get('allow_selfClose', True) else Button(style=ButtonStyle.red, custom_id="-allow_selfClose True")
    milestone = Button(style=ButtonStyle.green, custom_id="-allow_milestoneAdding False") if settings.get('allow_milestoneAdding', False) else Button(style=ButtonStyle.red, custom_id="-allow_milestoneAdding True")

    close.label = "Self Close"
    close.emoji = "🔒"

    milestone.label = "Add to Milestone"
    milestone.emoji = "🐛"

    return [[close], [milestone]]

def loopThroughSettings(guild_settings, args):
    if '-allow_selfClose' in args:
        try:
            setting = args[args.index('-allow_selfClose') + 1]
        except IndexError:
            setting = 'True'
        setting = get_positivity(setting)
        guild_settings['allow_selfClose'] = setting if setting is not None else True
    if '-allow_milestoneAdding' in args:
        try:
            setting = args[args.index('-allow_milestoneAdding') + 1]
        except IndexError:
            setting = 'True'
        setting = get_positivity(setting)
        guild_settings['allow_milestoneAdding'] = setting if setting is not None else True
    return guild_settings


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

        loopedSettings = loopThroughSettings(guild_settings, args)

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
            embed = getSettingsEmbed(loopedSettings, ctx.author)
            buttons = getSettingsButtons(loopedSettings)
            await ctx.send(embed=embed, components=buttons)

    @commands.Cog.listener()
    async def on_button_click(self, res):
        member = await res.guild.fetch_member(res.user.id)
        if member is not None and (res.custom_id in settingsTrue or res.custom_id in settingsFalse):
            if member.guild_permissions.administrator:
                guild_settings = await self.bot.mdb.lookupsettings.find_one({"server": res.guild.id})
                if guild_settings is None:
                    guild_settings = {}

                splitCustomId = res.custom_id.split(" ")
                splitArg = (splitCustomId[0], splitCustomId[1])

                loopedSettings = loopThroughSettings(guild_settings, splitArg)
                await self.bot.mdb.lookupsettings.update_one({"server": str(res.guild.id)}, {"$set": loopedSettings}, upsert=True)

                guild_settings = await self.bot.mdb.lookupsettings.find_one({"server": str(res.guild.id)})

                embed = getSettingsEmbed(guild_settings, res.author)
                buttons = getSettingsButtons(guild_settings)
                await res.message.edit(embed=embed, components=buttons)
                await res.respond(type=6)
            else:
                await res.respond(content="You need 'Administrator' permissions to change settings on this server.")


def setup(bot):
    log.info("[Cogs] Settings...")
    bot.add_cog(Settings(bot))
