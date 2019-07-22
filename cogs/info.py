import datetime

import discord
import time

import utils.globals as GG
from discord.ext import commands
from utils import logger

log = logger.logger

def checkDays(date):
    now = date.fromtimestamp(time.time())
    diff = now - date
    days = diff.days
    return f"{days} {'day' if days == 1 else 'days'} ago"


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Shows info about server"""
        HUMANS = ctx.guild.members
        BOTS = []
        for h in HUMANS:
            if h.bot is True:
                BOTS.append(h)
                HUMANS.remove(h)

        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.add_field(name="Name", value=ctx.guild.name)
        embed.add_field(name="ID", value=ctx.guild.id)
        embed.add_field(name="Owner", value=f"{ctx.guild.owner.name}#{ctx.guild.owner.discriminator}")
        embed.add_field(name="Region", value=GG.REGION[ctx.guild.region])
        embed.add_field(name="Total | Humans | Bots", value=f"{len(ctx.guild.members)} | {len(HUMANS)} | {len(BOTS)}")
        embed.add_field(name="Verification Level", value=GG.VERIFLEVELS[ctx.guild.verification_level])
        text, voice = GG.countChannels(ctx.guild.channels)
        embed.add_field(name="Text Channels", value=str(text))
        embed.add_field(name="Voice Channels", value=str(voice))
        embed.add_field(name="Creation Date", value=f"{ctx.guild.created_at}\n{checkDays(ctx.guild.created_at)}")
        embed.set_thumbnail(url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['stats', 'info'])
    async def botinfo(self, ctx):
        """Shows info about bot"""
        em = discord.Embed(color=discord.Color.green(), description="GithubCrawler, a bot that does all issue tracking for 5eTools and the Crawler Emporium.")
        em.title = 'Bot Info'
        em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        em.add_field(name="Servers", value=str(len(ctx.bot.guilds)))
        total_members = sum(len(s.members) for s in self.bot.guilds)
        unique_members = set(self.bot.get_all_members())
        members = '%s total\n%s unique' % (total_members, len(unique_members))
        em.add_field(name='Members', value=members)
        em.add_field(name='Uptime', value=str(datetime.timedelta(seconds=round(time.monotonic() - self.start_time))))
        totalText = 0
        totalVoice = 0
        for g in ctx.bot.guilds:
            text, voice = GG.countChannels(g.channels)
            totalText += text
            totalVoice += voice
        em.add_field(name='Text Channels', value=f"{totalText}")
        em.add_field(name='Voice Channels', value=f"{totalVoice}")
        em.add_field(name='Source', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler)")
        em.add_field(name='Issue Tracker', value="[Click Here](https://github.com/CrawlerEmporium/GithubCrawler/issues)")
        em.add_field(name="About",
                     value='A multipurpose bot made by LordDusk#0001 .\n[Support Server](https://discord.gg/HEY6BWj)')
        em.set_footer(text=f"GithubCrawler {ctx.bot.version} | Powered by discord.py")
        await ctx.send(embed=em)

    @commands.command()
    async def support(self, ctx):
        em = GG.EmbedWithAuthor(ctx)
        em.title = 'Support Server'
        em.description = "So you want support for GithubCrawler? You can easily join my discord [here](https://discord.gg/HEY6BWj).\n" \
                         "This server allows you to ask questions about the bot. Do feature requests, and talk with other bot users!\n\n" \
                         "If you want to somehow support my developer, you can buy me a cup of coffee (or 2) [here](https://ko-fi.com/5ecrawler)"
        await ctx.send(embed=em)

def setup(bot):
    log.info("Loading Info Cog...")
    bot.add_cog(Info(bot))
