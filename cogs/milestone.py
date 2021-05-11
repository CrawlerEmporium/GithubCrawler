import utils.globals as GG

from discord.ext import commands
from models.milestone import Milestone
from utils import logger

log = logger.logger


class Milestones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def milestone(self, ctx):
        prefix = await self.bot.get_server_prefix(ctx.message)
        await ctx.send("**Valid options currently are:**\n"
                       f"```{prefix}milestone\n"
                       f"{prefix}milestone view <milestone_id>\n"
                       f"{prefix}milestone create <milestone_title>\n"
                       f"*Below are admin/manager commands*:\n"
                       f"{prefix}milestone title <milestone_id> <milestone_title>\n"
                       f"{prefix}milestone description <milestone_id> <milestone_description>\n"
                       f"{prefix}milestone add <milestone_id> <feature/bug_id>\n"
                       f"{prefix}milestone remove <milestone_id> <feature/bug_id>\n```")
                       # f"{prefix}milestone subscribe <feature/bug_id>\n```")

    @milestone.command(name='view')
    @commands.guild_only()
    async def milestoneView(self, ctx, _id):
        milestone = await Milestone.from_id(_id, ctx.guild.id)
        await ctx.send(embed=await milestone.get_embed())

    @milestone.command(name='create')
    @commands.guild_only()
    async def milestoneCreate(self, ctx, *, title):
        if await GG.isManager(ctx):
            milestone_id = await get_next_milestone_id(ctx.guild.id)
            milestone = await Milestone.new(ctx.message.author.id, ctx.guild.id, milestone_id, title)
            await milestone.commit()
            await ctx.send(content=f"Milestone `{milestone_id}` created", embed=await milestone.get_embed())

    @milestone.command(name='title')
    @commands.guild_only()
    async def milestoneTitle(self, ctx, _id, *, title):
        if await GG.isManager(ctx):
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            milestone.title = title
            await milestone.commit()
            await ctx.send(f"The title for Milestone `{milestone.milestone_id}` was successfully set to `{title}`")

    @milestone.command(name='description')
    @commands.guild_only()
    async def milestoneDescription(self, ctx, _id, *, description):
        if await GG.isManager(ctx):
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            milestone.description = description
            await milestone.commit()
            await ctx.send(f"The description for Milestone `{milestone.milestone_id}` was successfully set to `{description}`")

    @milestone.command(name='add')
    @commands.guild_only()
    async def milestoneAdd(self, ctx, _id, report_id):
        if await GG.isManager(ctx):
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            await ctx.send(await milestone.add_report(report_id))

    @milestone.command(name='remove')
    @commands.guild_only()
    async def milestoneRemove(self, ctx, _id, report_id):
        if await GG.isManager(ctx):
            milestone = await Milestone.from_id(_id, ctx.guild.id)
            await ctx.send(await milestone.remove_report(report_id))

    @milestone.command(name='subscribe')
    @commands.guild_only()
    async def milestoneSubscribe(self, ctx, _id):
        #TODO implementatation to subscribe to milestones
        pass


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
