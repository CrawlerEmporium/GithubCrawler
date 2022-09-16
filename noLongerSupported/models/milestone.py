import discord

from crawler_utilities.handlers.errors import CrawlerException
from crawler_utilities.utils.functions import splitDiscordEmbedField
from models.ticket import Ticket
import utils.globals as GG

STATUS = {
    -1: "Outdated", 0: "New", 1: "Closed", 2: "Resolved", 3: "Released"
}


class Milestone:
    collection = GG.MDB['Milestone']

    def __init__(self, owner: int, server: int, milestone_id: str, status: int = 0, title: str = '', description: str = '',
                 tickets: list = None,
                 subscribers: list = None):
        if tickets is None:
            tickets = []
        if subscribers is None:
            subscribers = []
        self.owner = owner
        self.server = server
        self.milestone_id = milestone_id
        self.title = title
        self.description = description
        self.tickets = tickets
        self.subscribers = subscribers
        self.status = status

    @classmethod
    async def new(cls, owner, server, milestone_id, title):
        inst = cls(owner, server, milestone_id, 0, title, description='', tickets=None, subscribers=None)
        return inst

    @classmethod
    def from_dict(cls, milestone_dict):
        return cls(**milestone_dict)

    def to_dict(self):
        return {"owner": self.owner, "server": self.server, "milestone_id": self.milestone_id, "status": self.status, "title": self.title,
                "description": self.description, "tickets": self.tickets, "subscribers": self.subscribers}

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
        if _id in self.tickets:
            return f"Ticket `{_id}` is already linked to milestone `{self.milestone_id}`."
        else:
            self.tickets.append(_id)
            ticket = await Ticket.from_id(_id, guild_id)
            if self.milestone_id not in ticket.milestone:
                ticket.milestone.append(self.milestone_id)
                await ticket.commit()
            await self.commit(guild_id)
            return f"Added ticket `{_id}` to milestone `{self.milestone_id}`."

    async def remove_report(self, _id, guild_id):
        if _id in self.tickets:
            self.tickets.remove(_id)
            ticket = await Ticket.from_id(_id, guild_id)
            if self.milestone_id in ticket.milestone:
                ticket.milestone.remove(self.milestone_id)
                await ticket.commit()
            await self.commit(guild_id)
            return f"Removed ticket `{_id}` from milestone `{self.milestone_id}`."
        else:
            return f"Ticket `{_id}` was not found in the linked tickets for milestone `{self.milestone_id}`."

    def subscribe(self, userId):
        """Ensures a user is subscribed to this ticket."""
        if userId not in self.subscribers:
            self.subscribers.append(userId)

    def unsubscribe(self, userId):
        """Ensures a user is not subscribed to this ticket."""
        if userId in self.subscribers:
            self.subscribers.remove(userId)

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
        openTickets = "**Open: **"
        resolved = 0
        resolvedTickets = "**Resolved: **"
        tickets = len(self.tickets)

        embed.add_field(name="Status", value=f"{STATUS.get(self.status)}", inline=False)

        embed.add_field(name="Total Tickets", value=f"{tickets}")
        for ticket in self.tickets:
            ticket = await Ticket.from_id(ticket, self.server)
            if ticket.severity == 6:
                open += 1
                openTickets += f"`{ticket.ticket_id}`: {ticket.title}\n"
            if ticket.severity == -1:
                resolved += 1
                resolvedTickets += f"`{ticket.ticket_id}`: {ticket.title}\n"

        reportString = f"{openTickets} {open}\n\n{resolvedTickets} {resolved}"

        embed.add_field(name="Open Tickets", value=f"{open}")
        embed.add_field(name="Resolved Tickets", value=f"{resolved}")
        await splitDiscordEmbedField(embed, reportString, "** **")

        embed.set_footer(text=f"Owner: {self.owner}")

        return embed


class MilestoneException(CrawlerException):
    pass
