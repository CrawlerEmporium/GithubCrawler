import asyncio
import datetime
import discord
import time

from discord.ext import commands
from discord.ext.commands import BucketType
from discord import ButtonStyle
from discord.ui import Button

from crawler_utilities.handlers import logger
from crawler_utilities.utils.embeds import EmbedWithAuthor

log = logger.logger


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @commands.command(aliases=['stats', 'info'])
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
                     value="[Click Here](https://discord.com/oauth2/authorize?client_id=602779023151595546&scope=bot&permissions=388176)")
        em.add_field(name='Source', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler)")
        em.add_field(name='Issue Tracker', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler/issues)")
        em.add_field(name="About",
                     value='A multipurpose bot made by LordDusk#0001 .\n[Support Server](https://discord.gg/HEY6BWj)')
        em.set_footer(text=f"IssueCrawler {ctx.bot.version} | Powered by discord.py")
        em.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=em)

    @commands.command()
    async def support(self, ctx):
        em = EmbedWithAuthor(ctx)
        em.title = 'Support Server'
        em.description = "For technical support for IssueCrawler, join the Crawler Emporium discord [here](https://discord.gg/HEY6BWj)!\n" \
                         "There you can ask questions about the bot, make feature requests, report issues and/or bugs (please include any error messages), learn about my other Crawler bots, and share with other crawler bot users!\n\n" \
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

    @commands.command()
    async def invite(self, ctx):
        em = EmbedWithAuthor(ctx)
        em.title = 'Invite Me!'
        em.description = "Hi, you can easily invite me to your own server by following [this link](" \
                         "https://discord.com/oauth2/authorize?client_id=602779023151595546&scope=bot&permissions=2147543120" \
                         "=536977472)!\n\n" \
                         "**Mandatory:**\n__Manage Messages__ - this allows the " \
                         "bot to remove messages from other users.\n\n" \
                         "__Attach Files__ - Some commands or replies will let the bot attach images/files, " \
                         "without this permission it will not be able too.\n\n" \
                         "__Add Reactions__ - For the Anon/Delivery the bot requires to be able to add reactions to " \
                         "messages that are send.\n\n" \
                         "Sadly, all the requested permissions ARE required for the correct operation of the bot on your server. __No support is given for permission problems.__"
        await ctx.send(embed=em)

    @commands.command(hidden=True)
    @commands.cooldown(1, 60, BucketType.user)
    @commands.max_concurrency(1, BucketType.user)
    async def multiline(self, ctx, *, cmds: str):
        """Runs each line as a separate command, with a 1 second delay between commands.
        Limited to 1 multiline every 60 seconds, with a max of 10 commands, due to abuse.
        Usage:
        "!multiline
        !command1
        !command2
        !command3"
        """
        cmds = cmds.splitlines()
        for c in cmds[:10]:
            ctx.message.content = c
            await self.bot.process_commands(ctx.message)
            await asyncio.sleep(1)


def setup(bot):
    log.info("[Cogs] Info...")
    bot.add_cog(Info(bot))
