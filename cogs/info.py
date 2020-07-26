import datetime
import discord
import time

from discord.ext import commands
from utils import logger
from utils.embeds import EmbedWithAuthor

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
        em.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar_url)
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
        em.set_thumbnail(url=ctx.bot.user.avatar_url)
        await ctx.send(embed=em)

    @commands.command()
    async def support(self, ctx):
        em = EmbedWithAuthor(ctx)
        em.title = 'Support Server'
        em.description = "So you want support for IssueCrawler? You can easily join my discord [here](https://discord.gg/HEY6BWj).\n" \
                         "This server allows you to ask questions about the bot. Do feature requests, and talk with other bot users!\n\n" \
                         "If you want to somehow support my developer, you can buy me a cup of coffee (or 2) [here](https://ko-fi.com/5ecrawler)\n" \
                         "Or maybe you can even pledge to their patreon [here](https://patreon.com/lorddusk)"
        await ctx.send(embed=em)

    @commands.command()
    async def invite(self, ctx):
        em = EmbedWithAuthor(ctx)
        em.title = 'Invite Me!'
        em.description = "Hi, you can easily invite me to your own server by following [this link](" \
                         "https://discord.com/oauth2/authorize?client_id=602779023151595546&scope=bot&permissions=388176" \
                         "=536977472)!\n\nSadly, all the requested permissions ARE required for the correct operation of the bot on your server. __No support is given for permission problems.__"
        await ctx.send(embed=em)



def setup(bot):
    log.info("[Cogs] Info...")
    bot.add_cog(Info(bot))
