import datetime
import discord
import re
from cachetools import LRUCache
from discord import ButtonStyle
from discord.ui import Button

from crawler_utilities.cogs.stats import track_google_analytics_event
from crawler_utilities.handlers.errors import CrawlerException
from crawler_utilities.utils.pagination import BotEmbedPaginator

import utils.globals as GG
from models.attachment import Attachment
from utils.functions import paginate
from crawler_utilities.utils.functions import splitDiscordEmbedField
from models.githubClient import GitHubClient
import calendar
import time

log = GG.log

PRIORITY = {
    -2: "Patch Pending", -1: "Resolved",
    0: "P0: Critical", 1: "P1: Very High", 2: "P2: High", 3: "P3: Medium", 4: "P4: Low", 5: "P5: Trivial",
    6: "Pending/Other", 7: "In Review"
}
PRIORITY_LABELS = {
    0: "P0: Critical", 1: "P1: Very High", 2: "P2: High", 3: "P3: Medium", 4: "P4: Low", 5: "P5: Trivial"
}
VALID_LABELS = (
    'bug', 'duplicate', 'featurereq', 'help wanted', 'invalid', 'wontfix', 'longterm', 'enhancement',
    'P0: Critical', 'P1: Very High', 'P2: High', 'P3: Medium', 'P4: Low', 'P5: Trivial', 'stale',
    '+10', '+15'
)
VERI_EMOJI = {
    -2: "\u2b07",  # DOWNVOTE
    -1: "\u274c",  # CROSS MARK
    0: "\u2139",  # INFORMATION SOURCE
    1: "\u2705",  # WHITE HEAVY CHECK MARK
    2: "\u2b06",  # UPVOTE
    3: "\U0001F937",  # SHRUG
}
VERI_KEY = {
    -2: "Downvote",
    -1: "Cannot Reproduce",
    0: "Note",
    1: "Can Reproduce",
    2: "Upvote",
    3: "Indifferent"
}

GITHUB_BASE = "https://github.com"
UPVOTE_REACTION = "\U0001f44d"
DOWNVOTE_REACTION = "\U0001f44e"
SHRUG_REACTION = "\U0001F937"
INFORMATION_REACTION = "\U00002139"
GITHUB_THRESHOLD = 5
GITHUB_THRESHOLD_5ET = 5

message_ids = {}


def each(result, error):
    i = 0
    if error:
        raise error
    elif result:
        message_ids[i] = result['ticket_id']


def getListenerURL(identifier, trackerId):
    try:
        server = next(
            (item for item in GG.BUG_LISTEN_CHANS if item['tracker'] == trackerId and item['identifier'] == identifier),
            None)
    except:
        return ""
    if server is not None and server['url'] is not None:
        return server['url']
    else:
        return ""


class Ticket:
    message_cache = LRUCache(maxsize=100)
    
    collection = GG.MDB['Tickets']
    servers = GG.MDB['Github']
    cursor = collection.find()
    cursor.each(callback=each)

    messageIds = message_ids

    def __init__(self, reporter, ticket_id: str, title: str, severity: int, verification: int, attachments: list,
                 message, upvotes: int = 0, downvotes: int = 0, shrugs: int = 0, github_issue: int = None,
                 github_repo: str = None, subscribers: list = None, is_bug: bool = True, is_support: bool = False, jumpUrl: str = None,
                 trackerId: int = None, assignee=None, milestone: list = None, opened=None, closed=None, thread=None, server_id=None, last_updated=None):
        if subscribers is None:
            subscribers = []
        if milestone is None:
            milestone = []
        if github_repo is None:
            github_repo = 'NoRepo'
        if message is None:
            message = 0
        if github_issue is None:
            github_issue = 0
        self.reporter = reporter
        self.ticket_id = ticket_id
        self.title = title
        self.severity = severity

        self.attachments = attachments
        self.message = int(message)
        self.subscribers = subscribers
        self.milestone = milestone

        self.repo: str = github_repo
        self.github_issue = int(github_issue)

        self.is_bug = is_bug
        self.is_support = is_support
        self.upvotes = upvotes
        self.downvotes = downvotes
        self.shrugs = shrugs

        self.verification = verification
        self.collection = GG.MDB['Tickets']
        self.jumpUrl = jumpUrl
        self.trackerId = trackerId
        self.assignee = assignee

        self.opened = opened
        self.closed = closed

        self.thread = thread
        self.server_id = server_id

        self.last_updated = last_updated

    @classmethod
    async def new(cls, reporter, ticket_id: str, title: str, attachments: list, is_bug=True, is_support=False, repo=None, jumpUrl=None, trackerId=None, assignee=None, milestone=None, thread=None, server_id=None, last_updated=None):
        subscribers = None
        if isinstance(reporter, int):
            subscribers = [reporter]
        ts = calendar.timegm(time.gmtime())
        inst = cls(reporter, ticket_id, title, 6, 0, attachments, None, subscribers=subscribers, is_bug=is_bug, is_support=is_support, github_repo=repo, jumpUrl=jumpUrl, trackerId=trackerId, assignee=assignee, milestone=milestone, opened=ts, thread=thread, server_id=server_id, last_updated=last_updated)
        return inst

    @classmethod
    async def new_from_issue(cls, repo_name, issue):
        attachments = [Attachment("GitHub", issue['body'])]
        title = issue['title']
        id_match = re.match(r'([A-Z]{3,})(-\d+)?\s', issue['title'])
        is_bug = 'featurereq' not in [lab['name'] for lab in issue['labels']]
        if id_match:
            identifier = id_match.group(1)
            ticket_num = await get_next_ticket_num(identifier)
            ticket_id = f"{identifier}-{ticket_num}"
            title = title[len(id_match.group(0)):]
        else:
            identifier = identifier_from_repo(repo_name)
            ticket_num = await get_next_ticket_num(identifier)
            ticket_id = f"{identifier}-{ticket_num}"

        ts = calendar.timegm(time.gmtime())
        return cls("GitHub", ticket_id, title, -1,
                   # pri is created at -1 for unresolve (which changes it to 6)
                   0, attachments, None, github_issue=issue['number'], github_repo=repo_name, is_bug=is_bug, opened=ts)

    @classmethod
    def from_dict(cls, ticket_dict):
        ticket_dict['attachments'] = [Attachment.from_dict(a) for a in ticket_dict['attachments']]
        return cls(**ticket_dict)

    def to_dict(self):
        return {
            'reporter': self.reporter, 'ticket_id': self.ticket_id, 'title': self.title, 'severity': self.severity,
            'verification': self.verification, 'upvotes': self.upvotes, 'downvotes': self.downvotes,
            'shrugs': self.shrugs,
            'attachments': [a.to_dict() for a in self.attachments], 'message': self.message,
            'github_issue': self.github_issue, 'github_repo': self.repo, 'subscribers': self.subscribers,
            'is_bug': self.is_bug, 'is_support': self.is_support, 'jumpUrl': self.jumpUrl, 'trackerId': self.trackerId, 'assignee': self.assignee,
            'milestone': self.milestone, 'opened': self.opened, 'closed': self.closed, 'thread': self.thread, 'server_id': self.server_id, 'last_updated': self.last_updated
        }

    @classmethod
    async def from_id(cls, ticket_id, guild_id):
        guild = await cls.servers.find_one({"server": guild_id})
        trackerChannels = []
        for channel in guild['listen']:
            trackerChannels.append(channel['tracker'])
        dbTicket = await cls.collection.find_one({"ticket_id": ticket_id.upper(), "trackerId": {"$in": trackerChannels}})
        if dbTicket is not None:
            del dbTicket['_id']
            try:
                ticket = cls.from_dict(dbTicket)
                return await cls.add_server_id_backwards(ticket, guild_id)
            except KeyError:
                raise TicketException(f"{ticket_id} Ticket not found.")
        else:
            try:
                dbTicket = await cls.collection.find_one({"ticket_id": ticket_id.upper(), "server_id": guild_id})
                del dbTicket['_id']
                try:
                    ticket = cls.from_dict(dbTicket)
                    return await cls.add_server_id_backwards(ticket, guild_id)
                except KeyError:
                    raise TicketException(f"{ticket_id} Ticket not found.")
            except:
                raise TicketException(f"{ticket_id} Ticket not found.")

    @classmethod
    async def add_server_id_backwards(cls, ticket, guild_id):
        if ticket.server_id is None:
            ticket.server_id = guild_id
            await ticket.commit()
        return ticket

    @classmethod
    async def from_message_id(cls, message_id):
        ticket = await cls.collection.find_one({"message": message_id})
        if ticket is not None:
            del ticket['_id']
            try:
                return cls.from_dict(ticket)
            except KeyError:
                raise TicketException("Ticket not found.")
        else:
            raise TicketException("Ticket not found.")

    @classmethod
    def from_github(cls, repo_name, issue_num):
        tickets = cls.collection.find_one({"github_repo": repo_name, "github_issue": issue_num})
        try:
            return cls.from_dict(
                next(r for r in tickets.values() if
                     r.get('github_issue') == issue_num and r.get('github_repo') == repo_name))
        except StopIteration:
            raise TicketException("Ticket not found.")

    def is_open(self):
        return self.severity >= 0

    async def setup_github(self, bot, serverId=None):
        if (self.repo is not None or self.repo != 'NoRepo'):
            if self.github_issue:
                raise TicketException("Issue is already on GitHub.")
            if self.is_bug:
                labels = ["bug"]
            elif self.is_support:
                labels = ["support"]
            else:
                labels = ["featurereq"]
            desc = await self.get_github_desc(bot, serverId)

            if self.repo != 'NoRepo':
                issue = await GitHubClient.get_instance().create_issue(self.repo, f"{self.ticket_id} {self.title}", desc, labels)
                log.info(f"Adding to Github: {self.repo}, {self.ticket_id}")
                self.github_issue = issue.number

            # await GitHubClient.get_instance().add_issue_to_project(issue.number, is_bug=self.is_bug)

    async def setup_message(self, bot, guildID, trackerChannel):
        view = discord.ui.View()
        if self.is_bug or self.is_support:
            view.add_item(Button(label=GG.SUBSCRIBE, style=ButtonStyle.primary, emoji="📢", row=0))
            view.add_item(Button(label=GG.INFORMATION, style=ButtonStyle.primary, emoji="ℹ️", row=0))
            view.add_item(Button(label=GG.NOTE, style=ButtonStyle.primary, emoji="📝", row=0))
            if self.thread is not None:
                url = (await bot.fetch_channel(self.thread)).jump_url
                view.add_item(Button(label=GG.THREAD, style=ButtonStyle.primary, emoji="🧵", row=0, url=url))
            view.add_item(Button(label=GG.RESOLVE, style=ButtonStyle.success, emoji="✔️", row=1))
        else:
            view.add_item(Button(label=GG.UPVOTE, style=ButtonStyle.success, emoji="⬆️", row=0))
            view.add_item(Button(label=GG.DOWNVOTE, style=ButtonStyle.danger, emoji="⬇️", row=0))
            view.add_item(Button(label=GG.SHRUG, style=ButtonStyle.secondary, emoji="🤷", row=0))
            view.add_item(Button(label=GG.SUBSCRIBE, style=ButtonStyle.primary, emoji="📢", row=1))
            view.add_item(Button(label=GG.INFORMATION, style=ButtonStyle.primary, emoji="ℹ️", row=1))
            view.add_item(Button(label=GG.NOTE, style=ButtonStyle.primary, emoji="📝", row=1))
            if self.thread is not None:
                url = (await bot.fetch_channel(self.thread)).jump_url
                view.add_item(Button(label=GG.THREAD, style=ButtonStyle.primary, emoji="🧵", row=1, url=url))
            view.add_item(Button(label=GG.RESOLVE, style=ButtonStyle.success, emoji="✔️", row=2))

        ticket_message = await bot.get_channel(trackerChannel).send(embed=await self.get_embed(), view=view)
        view.stop()

        self.message = ticket_message.id
        Ticket.messageIds[ticket_message.id] = self.ticket_id
        return ticket_message

    async def commit(self):
        self.last_updated = int(time.time())
        await self.collection.replace_one({"ticket_id": self.ticket_id}, self.to_dict(), upsert=True)

    async def get_embed(self, detailed=False, ctx=None):
        embed = discord.Embed()
        if isinstance(self.reporter, int):
            embed.add_field(name="Added By", value=f"<@{self.reporter}>")
        else:
            embed.add_field(name="Added By", value=self.reporter)
        if self.assignee is None:
            embed.add_field(name="Priority", value=PRIORITY.get(self.severity, "Unknown"))
        else:
            embed.add_field(name="Assigned to", value=f"<@{self.assignee}>")

        if self.is_bug:
            embed.colour = 0xed4245
            embed.set_footer(
                text=f"/view {self.ticket_id} for details or click the ℹ button")
        elif self.is_support:
            embed.colour = 0x8c8c8c
            embed.set_footer(
                text=f"/view {self.ticket_id} for details or click the ℹ button")
        else:
            embed.colour = 0x3ba55d
            embed.add_field(name="Votes", value="\u2b06 " + str(self.upvotes) + " **|** \u2b07 " + str(
                self.downvotes) + " **|** \U0001F937 " + str(self.shrugs))
            vote_msg = "Vote by reacting"
            if self.repo != "NoRepo":
                if not self.github_issue:
                    vote_msg += f" | {GITHUB_THRESHOLD} upvotes required to track"
            embed.set_footer(text=f"/view {self.ticket_id} for details or click the ℹ button | {vote_msg}")

        if self.milestone is not None and len(self.milestone) > 0:
            embed.add_field(name="In milestone(s)", value=', '.join(self.milestone))

        if self.jumpUrl is not None:
            embed.add_field(name="Original Creation Link", value=f"[Click me]({self.jumpUrl})")

        embed.title = f"`{self.ticket_id}` {self.title}"
        if len(embed.title) > 256:
            embed.title = f"{embed.title[:250]}..."
        if self.github_issue:
            embed.url = f"{GITHUB_BASE}/{self.repo}/issues/{self.github_issue}"

        countNotes = 0
        for attachment in self.attachments:
            if attachment.veri == 0:
                countNotes += 1
        if countNotes == 1:
            embed.description = f"*{countNotes} note*"
        else:
            embed.description = f"*{countNotes} notes*"
        if detailed:
            countAttachments = 0
            for attachment in self.attachments:
                if countAttachments < 10:
                    if attachment.veri == 0 or attachment.veri == 1 or attachment.veri == -1:
                        if not ctx:
                            user = attachment.author
                        else:
                            if isinstance(attachment.author, int):
                                user = ctx.guild.get_member(attachment.author)
                            else:
                                user = attachment.author
                        if attachment.message is not None:
                            await splitDiscordEmbedField(embed, attachment.message,
                                                         f"{VERI_EMOJI.get(attachment.veri, '')} {user}")
                        else:
                            embed.add_field(name=f"{VERI_EMOJI.get(attachment.veri, '')} {user}", value="No details.", inline=False)
                        countAttachments += 1
            if countNotes >= 10:
                embed.description = f"*{countNotes} notes, showing first 10*"
            else:
                embed.description = f"*{countNotes} notes*"

        split = self.ticket_id.split("-")
        url = getListenerURL(split[0], self.trackerId)
        if split[0] == "R20":
            url = "https://cdn.discordapp.com/emojis/562116049475207178.png"

        if url == "" or url is None:
            embed.set_author(name=f"{self.ticket_id}")
        else:
            embed.set_author(name=f"{self.ticket_id}", icon_url=url)

        if self.last_updated is not None:
            embed.set_footer(text=f"{embed.footer.text} | Last Updated ")
            embed.timestamp = datetime.datetime.utcfromtimestamp(self.last_updated)

        return embed

    async def get_ticket_notes(self, ctx=None, msgToUse=None):
        attachments = self.attachments
        viewAttachments = []
        for attachment in attachments:
            if attachment.veri == 0 or attachment.veri == 1 or attachment.veri == -1:
                viewAttachments.append(attachment)

        pages = paginate(viewAttachments, 10)
        embeds = []
        for x in range(len(pages)):
            _choices = pages[x]

            embed = discord.Embed()
            if isinstance(self.reporter, int):
                embed.add_field(name="Added By", value=f"<@{self.reporter}>")
            else:
                embed.add_field(name="Added By", value=self.reporter)
            if self.assignee is None:
                embed.add_field(name="Priority", value=PRIORITY.get(self.severity, "Unknown"))
            else:
                embed.add_field(name="Assigned to", value=f"<@{self.assignee}>")
            if self.is_bug:
                embed.colour = 0xed4245
            elif self.is_support:
                embed.colour = 0x8c8c8c
            else:
                embed.colour = 0x3ba55d
                embed.add_field(name="Votes", value="\u2b06" + str(self.upvotes) + " **|** \u2b07" + str(
                    self.downvotes) + " **|** \U0001F937 " + str(self.shrugs))

            if self.milestone is not None and len(self.milestone) > 0:
                embed.add_field(name="In milestone(s)", value=', '.join(self.milestone))

            if self.jumpUrl is not None:
                embed.add_field(name="Original Creation Link", value=f"[Click me]({self.jumpUrl})")

            embed.title = f"`{self.ticket_id}` {self.title}"
            if len(embed.title) > 256:
                embed.title = f"{embed.title[:250]}..."
            if self.github_issue:
                embed.url = f"{GITHUB_BASE}/{self.repo}/issues/{self.github_issue}"

            for attachment in _choices:
                if attachment is not None:
                    if not ctx:
                        user = attachment.author
                    else:
                        if isinstance(attachment.author, int):
                            user = ctx.guild.get_member(attachment.author)
                        else:
                            user = attachment.author
                    if attachment.message is not None:
                        await splitDiscordEmbedField(embed, attachment.message, f"{VERI_EMOJI.get(attachment.veri, '')} {user}")
                    else:
                        embed.add_field(name=f"{VERI_EMOJI.get(attachment.veri, '')} {user}", value="No details.", inline=False)

            split = self.ticket_id.split("-")
            url = getListenerURL(split[0], self.trackerId)
            if split[0] == "R20":
                url = "https://cdn.discordapp.com/emojis/562116049475207178.png"

            if url == "" or url is None:
                embed.set_author(name=f"{self.ticket_id}")
            else:
                embed.set_author(name=f"{self.ticket_id}", icon_url=url)

            if self.last_updated is not None:
                embed.set_footer(text=f"{embed.footer.text} | Last Updated ")
                embed.timestamp = datetime.datetime.utcfromtimestamp(self.last_updated)

            embeds.append(embed)

        paginator = BotEmbedPaginator(ctx, pages=embeds, message=msgToUse)
        await paginator.run()

    async def get_github_desc(self, bot, serverId):
        msg = self.title
        if self.attachments:
            msg = self.attachments[0].message

        author = next((m for m in bot.get_all_members() if m.id == self.reporter), None)
        if author:
            desc = f"{msg}\n\n- {author}"
        else:
            desc = msg

        if not self.is_bug:
            i = 0
            for attachment in self.attachments[1:]:
                try:
                    guild = next(item for item in GG.GITHUBSERVERS if item.server == serverId)
                    if attachment.message and i >= guild.threshold:
                        continue
                except:
                    pass
                i += attachment.veri // 2
                msg = ''
                attachMessage = await self.get_attachment_message(bot, attachment, serverId)
                for line in attachMessage.strip().splitlines():
                    msg += f"> {line}\n"
                desc += f"\n\n{msg}"
            desc += f"\nVotes: +{self.upvotes} / -{self.downvotes} / ±{self.shrugs}"
        else:
            for attachment in self.attachments[1:]:
                if attachment.message:
                    continue
                msg = ''
                attachMessage = await self.get_attachment_message(bot, attachment, serverId)
                for line in attachMessage.strip().splitlines():
                    msg += f"> {line}\n"
                desc += f"\n\n{msg}"
            desc += f"\nVerification: {self.verification}"

        return desc

    def get_issue_link(self):
        if self.github_issue is None:
            return None
        return f"https://github.com/{self.repo}/issues/{self.github_issue}"

    async def add_attachment(self, ctx, serverId, attachment: Attachment, add_to_github=True):
        self.attachments.append(attachment)
        if add_to_github and self.github_issue and (self.repo is not None or self.repo != 'NoRepo'):
            if attachment.message:
                msg = await self.get_attachment_message(ctx.bot, attachment, serverId)
                await GitHubClient.get_instance().add_issue_comment(self.repo, self.github_issue, msg)

            if attachment.veri:
                gitDesc = await self.get_github_desc(ctx.bot, serverId)
                await GitHubClient.get_instance().edit_issue_body(self.repo, self.github_issue, gitDesc)

    async def get_attachment_message(self, bot, attachment: Attachment, guild_id):
        if isinstance(attachment.author, int):
            username = str(next((m for m in bot.get_all_members() if m.id == attachment.author), attachment.author))
        else:
            username = attachment.author

        if attachment.message is not None:
            reportIssue = await tickets_to_issues(attachment.message, guild_id)
            msg = f"{VERI_KEY.get(attachment.veri, '')} - {username}\n\n{reportIssue}"
        else:
            msg = f"{VERI_KEY.get(attachment.veri, '')} - {username}\n\n"
        return msg

    async def canrepro(self, author, msg, ctx, serverId):
        track_google_analytics_event("Can reproduce", f"{self.ticket_id}", f"{author}")
        if [a for a in self.attachments if a.author == author and a.veri == 1]:
            raise TicketException("You have already verified this ticket.")
        if not self.is_bug:
            raise TicketException("You cannot CR a feature request or support ticket.")
        attachment = Attachment.cr(author, msg)
        self.verification += 1
        await self.add_attachment(ctx, serverId, attachment)
        await self.notify_subscribers(ctx.bot, f"New CR by <@{author}>: {msg}")

    async def cannotrepro(self, author, msg, ctx, serverId):
        track_google_analytics_event("Can't reproduce", f"{self.ticket_id}", f"{author}")
        if [a for a in self.attachments if a.author == author and a.veri == -1]:
            raise TicketException("You have already verified this ticket.")
        if not self.is_bug:
            raise TicketException("You cannot CNR a feature request or support ticket.")
        attachment = Attachment.cnr(author, msg)
        self.verification -= 1
        await self.add_attachment(ctx, serverId, attachment)
        await self.notify_subscribers(ctx.bot, f"New CNR by <@{author}>: {msg}")

    async def upvote(self, author, msg, ctx, serverId):
        track_google_analytics_event("Upvote", f"{self.ticket_id}", f"{author}")
        for attachment in self.attachments:
            if attachment.author == author and attachment.veri == 2:
                raise TicketException(f"You have already upvoted {self.ticket_id}.")
            if attachment.author == author and attachment.veri == -2:
                self.downvotes -= 1
                self.attachments.remove(attachment)
            elif attachment.author == author and attachment.veri == 3:
                self.shrugs -= 1
                self.attachments.remove(attachment)

        if self.is_bug:
            raise TicketException("You cannot upvote a bug.")
        if self.is_support:
            raise TicketException("You cannot upvote a support ticket.")
        attachment = Attachment.upvote(author, msg)
        self.upvotes += 1
        await self.add_attachment(ctx, serverId, attachment)
        if msg:
            await self.notify_subscribers(ctx.bot, f"New Upvote by <@{author}>: {msg}")

        guild = next(item for item in GG.GITHUBSERVERS if item.server == serverId)
        if self.is_open() and not self.github_issue and self.upvotes - self.downvotes >= guild.threshold and (
                self.repo is not None or self.repo != 'NoRepo'):
            try:
                await self.setup_github(ctx.bot, serverId)
            except TicketException:
                log.info(f"Ticket {self.ticket_id} is already on GitHub, so no need to add it.")

        if self.upvotes - self.downvotes in (15, 10) and self.repo is not None and self.repo != 'NoRepo':
            await self.update_labels()

    async def downvote(self, author, msg, ctx, serverId):
        track_google_analytics_event("Downvote", f"{self.ticket_id}", f"{author}")
        for attachment in self.attachments:
            if attachment.author == author and attachment.veri == 2:
                self.upvotes -= 1
                self.attachments.remove(attachment)
            if attachment.author == author and attachment.veri == -2:
                raise TicketException(f"You have already downvoted {self.ticket_id}.")
            if attachment.author == author and attachment.veri == 3:
                self.shrugs -= 1
                self.attachments.remove(attachment)

        if self.is_bug:
            raise TicketException("You cannot downvote a bug.")
        if self.is_support:
            raise TicketException("You cannot downvote a support ticket.")
        attachment = Attachment.downvote(author, msg)
        self.downvotes += 1
        await self.add_attachment(ctx, serverId, attachment)
        if msg:
            await self.notify_subscribers(ctx.bot, f"New downvote by <@{author}>: {msg}")
        if self.upvotes - self.downvotes in (14, 9) and self.repo is not None and self.repo != 'NoRepo':
            await self.update_labels()

    async def indifferent(self, author, msg, ctx, serverId):
        track_google_analytics_event("Indifferent", f"{self.ticket_id}", f"{author}")
        for attachment in self.attachments:
            if attachment.author == author and attachment.veri == 2:
                self.upvotes -= 1
                self.attachments.remove(attachment)
            if attachment.author == author and attachment.veri == -2:
                self.downvotes -= 1
                self.attachments.remove(attachment)
            if attachment.author == author and attachment.veri == 3:
                raise TicketException(f"You were already indifferent about {self.ticket_id}.")

        if self.is_bug:
            raise TicketException("You cannot be indifferent about a bug.")
        if self.is_support:
            raise TicketException("You cannot be indifferent about a support ticket.")
        attachment = Attachment.indifferent(author, msg)
        self.shrugs += 1
        await self.add_attachment(ctx, serverId, attachment)

    async def addnote(self, author, msg, ctx, serverId, add_to_github=True):
        track_google_analytics_event("Note", f"{self.ticket_id}", f"{author}")
        attachment = Attachment(author, msg)
        await self.add_attachment(ctx, serverId, attachment, add_to_github)
        await self.notify_subscribers(ctx.bot, f"New note by <@{author}>: {msg}")

    async def force_accept(self, ctx, serverId):
        track_google_analytics_event("Force Accept", f"{self.ticket_id}", f"{serverId}")
        await self.setup_github(ctx.bot, serverId)

    async def force_deny(self, ctx, serverId):
        track_google_analytics_event("Force Deny", f"{self.ticket_id}", f"{serverId}")
        await self.notify_subscribers(ctx.bot, f"Ticket closed.")
        ts = calendar.timegm(time.gmtime())
        self.closed = ts
        guild = next(item for item in GG.GITHUBSERVERS if item.server == serverId)
        await self.addnote(guild.admin, f"Resolved - This ticket was denied.", ctx, serverId)

        msg_ = await self.get_message(ctx, serverId)
        if msg_:
            try:
                await msg_.delete()
                if self.message in Ticket.message_cache:
                    del Ticket.message_cache[self.message]
                if self.message in Ticket.messageIds:
                    del Ticket.messageIds[self.message]
            finally:
                self.message = None

        if self.github_issue:
            await GitHubClient.get_instance().close_issue(self.repo, self.github_issue)

    def subscribe(self, userId):
        """Ensures a user is subscribed to this ticket."""
        track_google_analytics_event("Subscribe", f"{self.ticket_id}", f"{userId}")
        if userId not in self.subscribers:
            self.subscribers.append(userId)

    def unsubscribe(self, userId):
        """Ensures a user is not subscribed to this ticket."""
        track_google_analytics_event("Unsubscribe", f"{self.ticket_id}", f"{userId}")
        if userId in self.subscribers:
            self.subscribers.remove(userId)

    async def get_message(self, ctx, serverId):
        if self.message is None:
            return None
        elif self.message in self.message_cache:
            return self.message_cache[self.message]
        else:
            try:
                msg = await ctx.bot.get_channel(self.trackerId).fetch_message(self.message)
            except AttributeError:
                msg = await ctx.bot.get_channel(ctx.channel.id).fetch_message(self.message)
            if msg:
                Ticket.message_cache[self.message] = msg
            return msg

    async def delete_message(self, ctx, serverId):
        msg_ = await self.get_message(ctx, serverId)
        if msg_ is not None:
            try:
                await msg_.delete()
                if self.message in Ticket.message_cache:
                    del Ticket.message_cache[self.message]
                if self.message in Ticket.messageIds:
                    del Ticket.messageIds[self.message]
            except discord.HTTPException:
                pass
            except Exception as e:
                print(e)
            finally:
                self.message = None

    async def update(self, ctx, serverId):
        msg = await self.get_message(ctx, serverId)
        if msg is None and self.is_open():
            await self.setup_message(ctx.bot, serverId, self.trackerId)
        elif self.is_open():
            await msg.clear_reactions()
            view = discord.ui.View()
            if self.is_bug or self.is_support:
                view.add_item(Button(label=GG.SUBSCRIBE, style=ButtonStyle.primary, emoji="📢", row=0))
                view.add_item(Button(label=GG.INFORMATION, style=ButtonStyle.primary, emoji="ℹ️", row=0))
                view.add_item(Button(label=GG.NOTE, style=ButtonStyle.primary, emoji="📝", row=0))
                if self.thread is not None:
                    url = (await ctx.bot.fetch_channel(self.thread)).jump_url
                    view.add_item(Button(label=GG.THREAD, style=ButtonStyle.primary, emoji="🧵", row=0, url=url))
                view.add_item(Button(label=GG.RESOLVE, style=ButtonStyle.success, emoji="✔️", row=1))
            else:
                view.add_item(Button(label=GG.UPVOTE, style=ButtonStyle.success, emoji="⬆️", row=0))
                view.add_item(Button(label=GG.DOWNVOTE, style=ButtonStyle.danger, emoji="⬇️", row=0))
                view.add_item(Button(label=GG.SHRUG, style=ButtonStyle.secondary, emoji="🤷", row=0))
                view.add_item(Button(label=GG.SUBSCRIBE, style=ButtonStyle.primary, emoji="📢", row=1))
                view.add_item(Button(label=GG.INFORMATION, style=ButtonStyle.primary, emoji="ℹ️", row=1))
                view.add_item(Button(label=GG.NOTE, style=ButtonStyle.primary, emoji="📝", row=1))
                if self.thread is not None:
                    url = (await ctx.bot.fetch_channel(self.thread)).jump_url
                    view.add_item(Button(label=GG.THREAD, style=ButtonStyle.primary, emoji="🧵", row=1, url=url))
                view.add_item(Button(label=GG.RESOLVE, style=ButtonStyle.success, emoji="✔️", row=2))

            await msg.edit(embed=await self.get_embed(), view=view)
            view.stop()

    async def resolve(self, ctx, serverId, msg='', close_github_issue=True, pend=False, ignore_closed=False):
        if self.severity == -1 and not ignore_closed:
            raise TicketException("This ticket is already closed.")

        self.severity = -1
        ts = calendar.timegm(time.gmtime())
        self.closed = ts

        if pend:
            await self.notify_subscribers(ctx.bot, f"Ticket resolved - a patch is pending.")
        else:
            await self.notify_subscribers(ctx.bot, f"Ticket resolved.")

        if msg:
            await self.addnote(ctx.interaction.user.id, f"Resolved - {msg}", ctx, serverId)

        track_google_analytics_event("Resolve", f"{self.ticket_id}", f"{serverId}")
        await self.delete_message(ctx, serverId)

        if close_github_issue and self.github_issue and (self.repo is not None or self.repo != 'NoRepo'):
            extra_labels = set()
            if msg.startswith('dupe'):
                extra_labels.add("duplicate")
            for label_match in re.finditer(r'\[(.+?)]', msg):
                label = label_match.group(1)
                if label in VALID_LABELS:
                    extra_labels.add(label)
            if extra_labels:
                await GitHubClient.get_instance().label_issue(self.repo, self.github_issue,
                                                              self.get_labels() + list(extra_labels))
            await GitHubClient.get_instance().close_issue(self.repo, self.github_issue)

        if self.thread is not None:
            channel = await ctx.bot.fetch_channel(self.thread)
            name = channel.name
            extra = len(f"{self.ticket_id} - ")
            extra += len(f"[Resolved] ")
            maxThreadTitleLength = 97 - extra
            if len(name) > maxThreadTitleLength:
                await channel.edit(name=f"[Resolved] - {name[:maxThreadTitleLength]}...", auto_archive_duration=1440)
            else:
                await channel.edit(name=f"[Resolved] - {name}", auto_archive_duration=1440)
            await channel.send(f"{msg}\n\nThis thread will now automatically archive itself in 1 day.")

        if pend:
            await self.pend()

    async def unresolve(self, ctx, serverId, msg='', open_github_issue=True):
        if not self.severity == -1:
            raise TicketException("This ticket is still open.")

        self.severity = 6
        self.closed = None
        await self.notify_subscribers(ctx.bot, f"Ticket unresolved.")
        if msg:
            await self.addnote(ctx.interaction.user.id, f"Unresolved - {msg}", ctx, serverId)

        track_google_analytics_event("Unresolve", f"{self.ticket_id}", f"{serverId}")
        await self.setup_message(ctx.bot, serverId, self.trackerId)

        if open_github_issue and self.github_issue and (self.repo is not None or self.repo != 'NoRepo'):
            await GitHubClient.get_instance().open_issue(self.repo, self.github_issue)

    async def untrack(self, ctx, serverId):
        await self.delete_message(ctx, serverId)
        if self.github_issue:
            await GitHubClient.get_instance().rename_issue(self.repo, self.github_issue, self.title)

        await self.collection.delete_one({"ticket_id": self.ticket_id})

    async def pend(self):
        collection = GG.MDB['PendingTickets']
        await collection.insert_one(self.ticket_id)

    def get_labels(self):
        labels = [PRIORITY_LABELS.get(self.severity)]
        if self.is_bug:
            labels.append("bug")
        elif self.is_support:
            labels.append("support")
        else:
            labels.append("featurereq")
            if self.upvotes - self.downvotes > 14:
                labels.append('+15')
            elif self.upvotes - self.downvotes > 9:
                labels.append('+10')
        return [l for l in labels if l]

    async def update_labels(self):
        labels = self.get_labels()
        await GitHubClient.get_instance().label_issue(self.repo, self.github_issue, labels)

    async def edit_title(self, new_title, idnum=""):
        self.title = new_title
        githubTitle = f"{idnum}{new_title}"
        await GitHubClient.get_instance().rename_issue(self.repo, self.github_issue, githubTitle)

    async def notify_subscribers(self, bot, msg):
        msg = f"`{self.ticket_id}` - {self.title}: {msg}"
        for sub in self.subscribers:
            try:
                member = next(m for m in bot.get_all_members() if m.id == sub)
                await member.send(msg)
            except (StopIteration, discord.HTTPException):
                continue


async def get_next_ticket_num(identifier, server):
    ticketNum = await GG.MDB.TicketNums.find_one({'key': f'{identifier}', 'server': server})
    if ticketNum is not None:
        num = ticketNum['amount'] + 1
        ticketNum['amount'] += 1
        num = formatNumber(num)
        await GG.MDB.TicketNums.replace_one({"key": f'{identifier}', 'server': server}, ticketNum)
        return f"{num}"
    else:
        raise TicketException(f"The bot couldn't find the `{identifier}` identifier.\n"
                              f"**__THIS IS A BUG__**\n"
                              f"Report this in the support discord ``/support``.")


def formatNumber(num):
    if num % 1 == 0:
        return int(num)
    else:
        return num


async def tickets_to_issues(text, guild_id):
    """
    Parses all XXX-### identifiers and adds a link to their GitHub Issue numbers.
    """
    if text is not None:
        regex = re.findall(r"(\w+-\d+)", text)
        for x in regex:
            ticket_id = x
            try:
                ticket = await Ticket.from_id(ticket_id, guild_id)
                con = True
                if ticket.repo and con:
                    text = text.replace(x, f"{ticket_id} ({ticket.repo}#{ticket.github_issue})")
                    con = False
                if ticket.github_issue and con:
                    text = text.replace(x, f"{ticket_id} (#{ticket.github_issue})")
            except TicketException:
                pass
    return text


def identifier_from_repo(repo_name):
    return GG.REPO_ID_MAP.get(repo_name, 'BUG')


class TicketException(CrawlerException):
    pass
