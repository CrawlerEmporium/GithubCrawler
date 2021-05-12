import discord
from disputils import BotEmbedPaginator

import utils.globals as GG

from discord.ext import commands
from models.milestone import Milestone, STATUS, MilestoneException
from utils import logger
from utils.libs.reports import Report

log = logger.logger


class Milestones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def milestone(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```"
                       f"{prefix}milestone\n"
                       f"{prefix}milestone view <milestone_id>\n"
                       f"{prefix}milestone list\n"
                       f"{prefix}milestone subscribe <milestone_id>\n"
                       f"{prefix}milestone unsubscribe <milestone_id>\n"
                       f"```"
                       f"*Below are admin/manager commands*:\n"
                       f"```"
                       f"{prefix}milestone create <milestone_title>\n"
                       f"{prefix}milestone title <milestone_id> <milestone_title>\n"
                       f"{prefix}milestone description <milestone_id> <milestone_description>\n"
                       f"{prefix}milestone status <milestone_id> <status_id>\n"
                       f"{prefix}milestone close <milestone_id>\n"
                       f"{prefix}milestone resolve <milestone_id>\n"
                       f"{prefix}milestone add <milestone_id> <feature/bug_id>\n"
                       f"{prefix}milestone remove <milestone_id> <feature/bug_id>\n"
                       f"```")

    @milestone.command(name='view')
    @commands.guild_only()
    async def milestoneView(self, ctx, _id):
        try:
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            await ctx.send(embed=await milestone.get_embed())
        except MilestoneException as e:
            await ctx.send(e)

    @milestone.command(name='list')
    @commands.guild_only()
    async def milestoneList(self, ctx):
        milestones = await GG.MDB.Milestone.find({"server": ctx.guild.id}).to_list(length=None)
        if len(milestones) == 0:
            await ctx.send("This server does not have any milestones currently.")
        else:
            embeds = list_embed(milestones, ctx.author)
            paginator = BotEmbedPaginator(ctx, embeds)
            await paginator.run()

    @milestone.command(name='subscribe')
    @commands.guild_only()
    async def milestoneSubscribe(self, ctx, _id):
        try:
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            for rep in milestone.reports:
                report = await Report.from_id(rep.report_id)
                report.subscribe(ctx)
                await report.commit()
            await ctx.send(f"Subscribed to {len(milestone.reports)} reports, all linked to `{milestone.milestone_id}`.")
        except MilestoneException as e:
            await ctx.send(e)

    @milestone.command(name='unsubscribe')
    @commands.guild_only()
    async def milestoneSubscribe(self, ctx, _id):
        try:
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            for rep in milestone.reports:
                report = await Report.from_id(rep.report_id)
                report.unsubscribe(ctx)
                await report.commit()
            await ctx.send(f"Unsubscribed to {len(milestone.reports)} reports, all linked to `{milestone.milestone_id}`.")
        except MilestoneException as e:
            await ctx.send(e)

    @milestone.command(name='create')
    @commands.guild_only()
    async def milestoneCreate(self, ctx, *, title):
        if await GG.isManager(ctx):
            milestone_id = await get_next_milestone_id(ctx.guild.id)
            milestone = await Milestone.new(ctx.message.author.id, ctx.guild.id, milestone_id, title)
            await milestone.commit(ctx.guild.id)
            await ctx.send(content=f"Milestone `{milestone_id}` created", embed=await milestone.get_embed())

    @milestone.command(name='title')
    @commands.guild_only()
    async def milestoneTitle(self, ctx, _id, *, title):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                milestone.title = title
                await milestone.commit(ctx.guild.id)
                await ctx.send(f"The title for Milestone `{milestone.milestone_id}` was successfully set to `{title}`")
            except MilestoneException as e:
                await ctx.send(e)

    @milestone.command(name='description')
    @commands.guild_only()
    async def milestoneDescription(self, ctx, _id, *, description):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                milestone.description = description
                await milestone.commit(ctx.guild.id)
                await ctx.send(
                    f"The description for Milestone `{milestone.milestone_id}` was successfully set to `{description}`")
            except MilestoneException as e:
                await ctx.send(e)

    @milestone.command(name='add')
    @commands.guild_only()
    async def milestoneAdd(self, ctx, _id, report_id):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                await ctx.send(await milestone.add_report(report_id, ctx.guild.id))
            except MilestoneException as e:
                await ctx.send(e)

    @milestone.command(name='remove')
    @commands.guild_only()
    async def milestoneRemove(self, ctx, _id, report_id):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                await ctx.send(await milestone.remove_report(report_id, ctx.guild.id))
            except MilestoneException as e:
                await ctx.send(e)

    @milestone.command(name='status')
    @commands.guild_only()
    async def milestoneStatus(self, ctx, _id=None, status: int = 0):
        if await GG.isManager(ctx):
            if _id is not None and status in STATUS:
                try:
                    milestone = await Milestone.from_id(_id, ctx.guild.id)
                    milestone.status = status
                    await milestone.commit(ctx.guild.id)
                    await ctx.send(f"Updated `{milestone.milestone_id}` to `{STATUS.get(status)}`\n")
                except MilestoneException as e:
                    await ctx.send(e)
            else:
                await ctx.send(f"Status {status}, is not a valid status, you can use the following statuses:\n"
                               f"```-1: Outdated\n"
                               f"0: New\n"
                               f"1: Closed\n"
                               f"2: Released```")

    @milestone.command(name='close')
    @commands.guild_only()
    async def milestoneClose(self, ctx, _id):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                milestone.status = 1
                await milestone.commit(ctx.guild.id)
                await ctx.send(f"Closed `{milestone.milestone_id}`")
            except MilestoneException as e:
                await ctx.send(e)

    @milestone.command(name='resolve')
    @commands.guild_only()
    async def milestoneResolve(self, ctx, _id):
        if await GG.isManager(ctx):
            try:
                milestone = await Milestone.from_id(_id, ctx.guild.id)
                milestone.status = 2
                await milestone.commit(ctx.guild.id)
                await ctx.send(f"Resolved `{milestone.milestone_id}`")
            except MilestoneException as e:
                await ctx.send(e)


def setup(bot):
    log.info("[Cogs] Milestone...")
    bot.add_cog(Milestones(bot))


async def get_next_milestone_id(server):
    reportNum = await GG.MDB.MilestoneNums.find_one({'server': server})
    if reportNum is None:
        await GG.MDB.MilestoneNums.insert_one({'server': server, 'amount': 0})
        reportNum = {'server': server, 'amount': 0}
    num = reportNum['amount'] + 1
    reportNum['amount'] += 1
    if num % 1 == 0:
        num = int(num)
    await GG.MDB.MilestoneNums.replace_one({'server': server}, reportNum)
    return f"MS{num}"


def list_embed(list_personals, author):
    embedList = []
    for i in range(0, len(list_personals), 10):
        lst = list_personals[i:i + 10]
        desc = ""
        for item in lst:
            item.pop("_id")
            milestone = Milestone.from_dict(item)
            desc += f'• `{milestone.milestone_id} - ' + str(milestone.title) + '`\n'
        if isinstance(author, discord.Member) and author.color != discord.Colour.default():
            embed = discord.Embed(description=desc, color=author.color)
        else:
            embed = discord.Embed(description=desc)
        embed.set_author(name='Milestones', icon_url=author.avatar_url)
        embedList.append(embed)
    return embedList
