import asyncio
import discord
from discord.ext import commands

from utils import checks
from utils import globals as GG
from utils import logger
from utils.embeds import EmbedWithAuthor

log = logger.logger


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx):
        if GG.checkPermission(ctx, "ar"):
            prefix = await self.bot.get_server_prefix(ctx.message)
            embed = await self.helpCommand(ctx, prefix)
            message = await ctx.send(embed=embed)
            await message.add_reaction('🔎')
            await message.add_reaction('🔍')
            await message.add_reaction('📖')
            await message.add_reaction('🎚️')
            await message.add_reaction('❌')

            await self.waitChangeMessage(ctx, message)
        else:
            await ctx.invoke(self.bot.get_command("oldhelp"))

    async def waitChangeMessage(self, ctx, message):
        def check(reaction, user):
            return (user == ctx.message.author and str(reaction.emoji) == '🔎') or \
                   (user == ctx.message.author and str(reaction.emoji) == '📖') or \
                   (user == ctx.message.author and str(reaction.emoji) == '🔍') or \
                   (user == ctx.message.author and str(reaction.emoji) == '🎚️') or \
                   (user == ctx.message.author and str(reaction.emoji) == '❌')

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            if not isinstance(message.channel, discord.DMChannel):
                await message.clear_reactions()
        else:
            prefix = await self.bot.get_server_prefix(ctx.message)
            embed = None
            if str(reaction.emoji) == '🔎':
                embed = await self.issueCommand(ctx, prefix)
            if str(reaction.emoji) == '🔍':
                embed = await self.issueStaffCommand(ctx, prefix)
            if str(reaction.emoji) == '📖':
                embed = await self.trackerCommand(ctx, prefix)
            if str(reaction.emoji) == '🎚️':
                embed = await self.settingsCommand(ctx, prefix)
            if str(reaction.emoji) == '❌':
                await message.delete()
                if not isinstance(message.channel, discord.DMChannel):
                    await ctx.message.delete()
            if embed is not None:
                await message.edit(embed=embed)
                if not isinstance(message.channel, discord.DMChannel):
                    await reaction.remove(user)
                else:
                    await self.waitChangeMessage(ctx, message)

    async def helpCommand(self, ctx, prefix):
        embed = EmbedWithAuthor(ctx)
        embed.title = "Help command with clickable categories."
        embed.add_field(name='🔎', value='Issue')
        embed.add_field(name='🔍', value='Staff Issue')
        embed.add_field(name='📖', value='Tracker')
        embed.add_field(name='🎚️', value='Settings')
        embed.add_field(name='❌', value='Deletes this message')
        embed.set_footer(text='These reactions are available for 60 seconds, afterwards it will stop responding.')
        return embed

    async def issueCommand(self, ctx, prefix):
        embed = EmbedWithAuthor(ctx)
        embed.title = "Commands to communicate with the bot."
        embed.add_field(name="cannotrepro", value=f"``{prefix}``\nAdds nonreproduction to a report.", inline=False)
        embed.add_field(name="canrepro", value=f"``{prefix}``\nAdds reproduction to a report.", inline=False)
        embed.add_field(name="downvote", value=f"``{prefix}``\nAdds a downvote to the selected feature request.", inline=False)
        embed.add_field(name="upvote", value=f"``{prefix}``\nAdds an upvote to the selected feature request.", inline=False)
        embed.add_field(name="note", value=f"``{prefix}``\nAdds a note to a report.", inline=False)
        embed.add_field(name="report", value=f"``{prefix}``\nGets the detailed status of a report.", inline=False)
        embed.add_field(name="subscribe", value=f"``{prefix}``\nSubscribes to a report.", inline=False)
        embed.add_field(name="unsuball", value=f"``{prefix}``\nUnsubscribes from all reports.", inline=False)
        embed.add_field(name="top", value=f"``{prefix}``\nGets top x or top 10", inline=False)
        embed.add_field(name="flop", value=f"``{prefix}``\nGets bottom x or bottom 10", inline=False)
        self.setFooter(embed)
        return embed

    async def issueStaffCommand(self, ctx, prefix):
        embed = EmbedWithAuthor(ctx)
        embed.title = "Commands to communicate with the bot as Server Owner."
        embed.add_field(name="priority", value=f"``{prefix}``\nChanges the priority of a report.", inline=False)
        embed.add_field(name="reidentify", value=f"``{prefix}``\nChanges the identifier of a report.", inline=False)
        embed.add_field(name="rename", value=f"``{prefix}``\nChanges the title of a report.", inline=False)
        embed.add_field(name="resolve", value=f"``{prefix}``\nResolves a report.", inline=False)
        embed.add_field(name="unresolve", value=f"``{prefix}``\nUnresolves a report.", inline=False)
        self.setFooter(embed)
        return embed

    async def trackerCommand(self, ctx, prefix):
        embed = EmbedWithAuthor(ctx)
        embed.title = "Commands to start using IssueCrawler."
        embed.add_field(name="issue", value=f"``{prefix}issue``\n", inline=False)
        embed.add_field(name="register", value=f"``{prefix}issue register``\n", inline=False)
        embed.add_field(name="channel", value=f"``{prefix}issue channel <type> <identifier> [tracker=0] [channel=0]``\n", inline=False)
        embed.add_field(name="trackers", value=f"``{prefix}issue trackers``\n", inline=False)
        self.setFooter(embed)
        return embed

    async def settingsCommand(self, ctx, prefix):
        embed = EmbedWithAuthor(ctx)
        embed.title = "Settings commands."
        embed.add_field(name="prefix", value=f"``{prefix}prefix``\nSets the bot's prefix for this server.", inline=False)
        self.setFooter(embed)
        return embed

    def setFooter(self, embed):
        embed.add_field(name="General Usage",
                        value='**|**\tmeans you can use either of the commands\n'
                              '**<>**\tmeans that part of the command is required.\n'
                              '**[]**\tmeans it is an optional part of the command.',
                        inline=False)
        embed.set_footer(
            text="These reactions are available for 60 seconds, afterwards it will stop responding.\n\n📔 Returns to the main menu.\n❌ Deletes this message from chat.'")


def setup(bot):
    log.info("[Cogs] Help...")
    bot.add_cog(Help(bot))
