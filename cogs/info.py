import asyncio
import datetime
import discord
import time

from discord.ext import commands
from discord.ext.commands import BucketType
from discord import ButtonStyle, slash_command
from discord.ui import Button

from crawler_utilities.utils.embeds import EmbedWithRandomColor
from utils import globals as GG
log = GG.log


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @slash_command(name="info")
    async def botinfo(self, ctx):
        """Shows info about bot"""
        em = discord.Embed(color=discord.Color.green(), description="IssueCrawler, a bug and feature request tracker for Discord.")
        em.title = 'Bot Info'
        em.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.display_avatar.url)
        em.add_field(name="Servers", value=str(len(ctx.bot.guilds)))
        total_members = sum(len(s.members) for s in self.bot.guilds)
        unique_members = set(self.bot.get_all_members())
        members = '%s total\n%s unique' % (total_members, len(unique_members))
        em.add_field(name='Uptime', value=str(datetime.timedelta(seconds=round(time.monotonic() - self.start_time))))
        em.add_field(name="** **", value="** **")
        em.add_field(name='Members', value=members)
        em.add_field(name="** **", value="** **")
        em.add_field(name="** **", value="** **")
        em.add_field(name="Invite",
                     value="[Click Here](https://discord.com/oauth2/authorize?client_id=602779023151595546&scope=bot%20applications.commands&permissions=388176=536977472)")
        em.add_field(name='Source', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler)")
        em.add_field(name='Issue Tracker', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler/issues)")
        em.add_field(name="About",
                     value='A multipurpose bot made by LordDusk#0001.\n[Support Server](https://discord.gg/HEY6BWj)\n[Website](https://crawleremporium.com/)')
        em.set_footer(text=f"IssueCrawler {ctx.bot.version} | Powered by discord.py")
        em.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        await ctx.respond(embed=em)

    @slash_command(name="support")
    async def support(self, ctx):
        em = EmbedWithRandomColor()
        em.title = 'Support Server'
        em.description = "For technical support for IssueCrawler, join the Crawler Emporium discord [here](https://discord.gg/HEY6BWj)!\n" \
                         "There you can ask questions about the bot, make feature requests, ticket issues and/or bugs (please include any error messages), learn about my other Crawler bots, and share with other crawler bot users!\n\n" \
                         "[Check the Website](https://crawleremporium.com) for even more information.\n\n" \
                         "To add premium features to the bot, [<:Patreon:855754853153505280> Join the Patreon](https://www.patreon.com/LordDusk), or if you'd rather show just appreciation [tip the Developer a <:Kofi:855758703772958751> here](https://ko-fi.com/5ecrawler)."
        serverEmoji = self.bot.get_emoji(int("<:5e:603932658820448267>".split(":")[2].replace(">", "")))
        patreonEmoji = self.bot.get_emoji(int("<:Patreon:855754853153505280>".split(":")[2].replace(">", "")))
        kofiEmoji = self.bot.get_emoji(int("<:Kofi:855758703772958751>".split(":")[2].replace(">", "")))
        view = discord.ui.View()
        view.add_item(Button(label="Discord", style=ButtonStyle.url, emoji=serverEmoji, url="https://discord.gg/HEY6BWj"))
        view.add_item(Button(label="Website", style=ButtonStyle.url, url="https://www.crawleremporium.com"))
        view.add_item(Button(label="Patreon", style=ButtonStyle.url, emoji=patreonEmoji, url="https://www.patreon.com/LordDusk"))
        view.add_item(Button(label="Buy me a coffee", style=ButtonStyle.url, emoji=kofiEmoji, url="https://ko-fi.com/5ecrawler"))
        await ctx.send(embed=em, view=view)


def setup(bot):
    log.info("[Cogs] Info...")
    bot.add_cog(Info(bot))
