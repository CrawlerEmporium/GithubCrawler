import discord

from utils.libs.reports import Report
import utils.globals as GG


class Milestone:
    collection = GG.MDB['Milestone']

    def __init__(self, owner: int, server: int, milestone_id: str, title: str = '', description: str = '',
                 reports: list = None):
        if reports is None:
            reports = []
        self.owner = owner
        self.server = server
        self.milestone_id = milestone_id
        self.title = title
        self.description = description
        self.reports = reports

    @classmethod
    async def new(cls, owner, server, milestone_id, title):
        inst = cls(owner, server, milestone_id, title, description='', reports=None)
        return inst

    @classmethod
    def from_dict(cls, milestone_dict):
        return cls(**milestone_dict)

    def to_dict(self):
        return {"owner": self.owner, "server": self.server, "milestone_id": self.milestone_id, "title": self.title,
                "description": self.description, "reports": self.reports}

    @classmethod
    async def from_id(cls, milestone_id, server):
        id = milestone_id.upper()
        milestone = await cls.collection.find_one({"milestone_id": id, "server": server})
        if milestone is not None:
            del milestone['_id']
            try:
                return cls.from_dict(milestone)
            except KeyError:
                raise MilestoneException(f"`{id}` Milestone not found.")
        else:
            raise MilestoneException(f"`{id}` Milestone not found.")

    async def add_report(self, _id):
        if _id in self.reports:
            return f"Report `{_id}` is already linked to milestone `{self.milestone_id}`."
        else:
            self.reports.append(_id)
            report = await Report.from_id(_id)
            if self.milestone_id not in report.milestone:
                report.milestone.append(self.milestone_id)
                await report.commit()
            await self.commit()
            return f"Added report `{_id}` to milestone `{self.milestone_id}`."

    async def remove_report(self, _id):
        if _id in self.reports:
            self.reports.remove(_id)
            report = await Report.from_id(_id)
            if self.milestone_id in report.milestone:
                report.milestone.remove(self.milestone_id)
                await report.commit()
            await self.commit()
            return f"Removed report `{_id}` from milestone `{self.milestone_id}`."
        else:
            return f"Report `{_id}` was not found in the linked reports for milestone `{self.milestone_id}`."

    async def commit(self):
        await self.collection.replace_one({"milestone_id": self.milestone_id}, self.to_dict(), upsert=True)

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

        embed.add_field(name="Total Tickets", value=f"{reports}")
        for report in self.reports:
            report = await Report.from_id(report)
            if report.severity == 6:
                open += 1
                openReports += f"\n`{report.report_id}`: {report.title}"
            if report.severity == -1:
                resolved += 1
                resolvedReports += f"\n`{report.report_id}`: {report.title}"

        reportString = f"{openReports} {open}\n\n{resolvedReports} {resolved}"

        embed.add_field(name="Open Tickets", value=f"{open}")
        embed.add_field(name="Resolved Tickets", value=f"{resolved}")

        embed.add_field(name="** **", value=f"{reportString}")

        embed.set_footer(text=f"Owner: {self.owner}")

        return embed


class MilestoneException(Exception):
    pass
