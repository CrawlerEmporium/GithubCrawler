import discord

from crawler_utilities.utils.functions import splitDiscordEmbedField
from utils.libs.reports import Report
import utils.globals as GG

STATUS = {
    -1: "Outdated", 0: "New", 1: "Closed", 2: "Resolved", 3: "Released"
}

class Milestone:
    collection = GG.MDB['Milestone']

    def __init__(self, owner: int, server: int, milestone_id: str, status: int = 0, title: str = '', description: str = '',
                 reports: list = None,
                 subscribers: list = None):
        if reports is None:
            reports = []
        if subscribers is None:
            subscribers = []
        self.owner = owner
        self.server = server
        self.milestone_id = milestone_id
        self.title = title
        self.description = description
        self.reports = reports
        self.subscribers = subscribers
        self.status = status

    @classmethod
    async def new(cls, owner, server, milestone_id, title):
        inst = cls(owner, server, milestone_id, 0, title, description='', reports=None, subscribers=None)
        return inst

    @classmethod
    def from_dict(cls, milestone_dict):
        return cls(**milestone_dict)

    def to_dict(self):
        return {"owner": self.owner, "server": self.server, "milestone_id": self.milestone_id, "status": self.status, "title": self.title,
                "description": self.description, "reports": self.reports, "subscribers": self.subscribers}

    @classmethod
    async def from_id(cls, milestone_id, server):
        id = milestone_id.upper()
        milestone = await cls.collection.find_one({"milestone_id": id, "server": server})
        if milestone is not None:
            del milestone['_id']
            try:
                return cls.from_dict(milestone)
            except KeyError:
                raise MilestoneException(f"Milestone `{id}` not found.")
        else:
            raise MilestoneException(f"Milestone `{id}` not found.")

    async def add_report(self, _id, guild_id):
        if _id in self.reports:
            return f"Report `{_id}` is already linked to milestone `{self.milestone_id}`."
        else:
            self.reports.append(_id)
            report = await Report.from_id(_id, guild_id)
            if self.milestone_id not in report.milestone:
                report.milestone.append(self.milestone_id)
                await report.commit()
            await self.commit(guild_id)
            return f"Added report `{_id}` to milestone `{self.milestone_id}`."

    async def remove_report(self, _id, guild_id):
        if _id in self.reports:
            self.reports.remove(_id)
            report = await Report.from_id(_id, guild_id)
            if self.milestone_id in report.milestone:
                report.milestone.remove(self.milestone_id)
                await report.commit()
            await self.commit(guild_id)
            return f"Removed report `{_id}` from milestone `{self.milestone_id}`."
        else:
            return f"Report `{_id}` was not found in the linked reports for milestone `{self.milestone_id}`."

    def subscribe(self, ctx):
        """Ensures a user is subscribed to this report."""
        if ctx.message.author.id not in self.subscribers:
            self.subscribers.append(ctx.message.author.id)

    def unsubscribe(self, ctx):
        """Ensures a user is not subscribed to this report."""
        if ctx.message.author.id in self.subscribers:
            self.subscribers.remove(ctx.message.author.id)

    async def notify_subscribers(self, bot, msg):
        msg = f"`{self.milestone_id}` - {self.title}: {msg}"
        for sub in self.subscribers:
            try:
                member = next(m for m in bot.get_all_members() if m.id == sub)
                await member.send(msg)
            except (StopIteration, discord.HTTPException):
                continue

    async def commit(self, guild_id):
        await self.collection.replace_one({"milestone_id": self.milestone_id, "server": guild_id}, self.to_dict(), upsert=True)

    async def get_embed(self):
        embed = discord.Embed()

        embed.title = f"`{self.milestone_id}` - {self.title}"
        if len(embed.title) > 256:
            embed.title = f"{embed.title[:250]}..."

        if len(self.description) > 0:
            embed.description = f"{self.description}"

        open = 0
        openReports = "**Open: **"
        resolved = 0
        resolvedReports = "**Resolved: **"
        reports = len(self.reports)

        embed.add_field(name="Status", value=f"{STATUS.get(self.status)}", inline=False)

        embed.add_field(name="Total Tickets", value=f"{reports}")
        for report in self.reports:
            report = await Report.from_id(report, self.server)
            if report.severity == 6:
                open += 1
                openReports += f"`{report.report_id}`: {report.title}\n"
            if report.severity == -1:
                resolved += 1
                resolvedReports += f"`{report.report_id}`: {report.title}\n"

        reportString = f"{openReports} {open}\n\n{resolvedReports} {resolved}"

        embed.add_field(name="Open Tickets", value=f"{open}")
        embed.add_field(name="Resolved Tickets", value=f"{resolved}")
        await splitDiscordEmbedField(embed, reportString, "** **")

        embed.set_footer(text=f"Owner: {self.owner}")

        return embed


class MilestoneException(Exception):
    pass
