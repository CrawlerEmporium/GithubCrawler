import discord
import re
from cachetools import LRUCache

import utils.globals as GG
from utils.libs.github import GitHubClient

PRIORITY = {
    -2: "Patch Pending", -1: "Resolved",
    0: "P0: Critical", 1: "P1: Very High", 2: "P2: High", 3: "P3: Medium", 4: "P4: Low", 5: "P5: Trivial",
    6: "Pending/Other"
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
}
VERI_KEY = {
    -2: "Downvote",
    -1: "Cannot Reproduce",
    0: "Note",
    1: "Can Reproduce",
    2: "Upvote"
}

TRACKER_CHAN_5ET = 593769144969723914
TRACKER_CHAN = 590812637072195587
TRACKER_CHAN_MPMB = 631432292245569536
TRACKER_CHAN_MPMB_BUG = 704677726287691786
GITHUB_BASE = "https://github.com"
UPVOTE_REACTION = "\U0001f44d"
DOWNVOTE_REACTION = "\U0001f44e"
INFORMATION_REACTION = "\U00002139"
GITHUB_THRESHOLD = 5
GITHUB_THRESHOLD_5ET = 5


class Attachment:
    def __init__(self, author, message: str = '', veri: int = 0):
        self.author = author
        self.message = message or None
        self.veri = veri

    @classmethod
    def from_dict(cls, attachment):
        return cls(**attachment)

    def to_dict(self):
        return {"author": self.author, "message": self.message, "veri": self.veri}

    @classmethod
    def upvote(cls, author, msg=''):
        return cls(author, msg, 2)

    @classmethod
    def downvote(cls, author, msg=''):
        return cls(author, msg, -2)

    @classmethod
    def cr(cls, author, msg=''):
        return cls(author, msg, 1)

    @classmethod
    def cnr(cls, author, msg=''):
        return cls(author, msg, -1)


message_ids = {}


def each(result, error):
    i = 0
    if error:
        raise error
    elif result:
        message_ids[i] = result['report_id']


class Report:
    message_cache = LRUCache(maxsize=100)

    collection = GG.MDB['Reports']
    cursor = collection.find()
    cursor.each(callback=each)

    messageIds = message_ids

    def __init__(self, reporter, report_id: str, title: str, severity: int, verification: int, attachments: list,
                 message, upvotes: int = 0, downvotes: int = 0, github_issue: int = None,
                 github_repo: str = None, subscribers: list = None, is_bug: bool = True, jumpUrl: str = None):
        if subscribers is None:
            subscribers = []
        if github_repo is None:
            github_repo = 'CrawlerEmporium/5eCrawler'
        if message is None:
            message = 0
        if github_issue is None:
            github_issue = 0
        self.reporter = reporter
        self.report_id = report_id
        self.title = title
        self.severity = severity

        self.attachments = attachments
        self.message = int(message)
        self.subscribers = subscribers

        self.repo: str = github_repo
        self.github_issue = int(github_issue)

        self.is_bug = is_bug
        self.upvotes = upvotes
        self.downvotes = downvotes

        self.verification = verification
        self.collection = GG.MDB['Reports']
        self.jumpUrl = jumpUrl

    @classmethod
    async def new(cls, reporter, report_id: str, title: str, attachments: list, is_bug=True, repo=None, jumpUrl=None):
        subscribers = None
        if isinstance(reporter, int):
            subscribers = [reporter]
        inst = cls(reporter, report_id, title, 6, 0, attachments, None, subscribers=subscribers, is_bug=is_bug,
                   github_repo=repo, jumpUrl=jumpUrl)
        return inst

    @classmethod
    async def new_from_issue(cls, repo_name, issue):
        attachments = [Attachment("GitHub", issue['body'])]
        title = issue['title']
        id_match = re.match(r'([A-Z]{3,})(-\d+)?\s', issue['title'])
        is_bug = 'featurereq' not in [lab['name'] for lab in issue['labels']]
        if id_match:
            identifier = id_match.group(1)
            report_num = await get_next_report_num(identifier)
            report_id = f"{identifier}-{report_num}"
            title = title[len(id_match.group(0)):]
        else:
            identifier = identifier_from_repo(repo_name)
            report_num = await get_next_report_num(identifier)
            report_id = f"{identifier}-{report_num}"

        return cls("GitHub", report_id, title, -1,
                   # pri is created at -1 for unresolve (which changes it to 6)
                   0, attachments, None, github_issue=issue['number'], github_repo=repo_name, is_bug=is_bug)

    @classmethod
    def from_dict(cls, report_dict):
        report_dict['attachments'] = [Attachment.from_dict(a) for a in report_dict['attachments']]
        return cls(**report_dict)

    def to_dict(self):
        return {
            'reporter': self.reporter, 'report_id': self.report_id, 'title': self.title, 'severity': self.severity,
            'verification': self.verification, 'upvotes': self.upvotes, 'downvotes': self.downvotes,
            'attachments': [a.to_dict() for a in self.attachments], 'message': self.message,
            'github_issue': self.github_issue, 'github_repo': self.repo, 'subscribers': self.subscribers,
            'is_bug': self.is_bug, 'jumpUrl': self.jumpUrl
        }

    @classmethod
    async def from_id(cls, report_id):
        report = await cls.collection.find_one({"report_id": report_id.upper()})
        del report['_id']
        try:
            return cls.from_dict(report)
        except KeyError:
            raise ReportException("Report not found.")

    @classmethod
    async def from_message_id(cls, message_id):
        report = await cls.collection.find_one({"message": message_id})
        if report is not None:
            del report['_id']
            try:
                return cls.from_dict(report)
            except KeyError:
                raise ReportException("Report not found.")
        else:
            raise ReportException("Report not found.")

    @classmethod
    def from_github(cls, repo_name, issue_num):
        reports = cls.collection.find_one({"github_repo": repo_name, "github_issue": issue_num})
        try:
            return cls.from_dict(
                next(r for r in reports.values() if
                     r.get('github_issue') == issue_num and r.get('github_repo') == repo_name))
        except StopIteration:
            raise ReportException("Report not found.")

    def is_open(self):
        return self.severity >= 0

    async def setup_github(self, ctx, serverId=None):
        if self.github_issue:
            raise ReportException("Issue is already on GitHub.")
        if self.is_bug:
            labels = ["bug"]
        else:
            labels = ["featurereq"]
        desc = await self.get_github_desc(ctx, serverId)

        issue = await GitHubClient.get_instance().create_issue(self.repo, f"{self.report_id} {self.title}", desc,
                                                               labels)
        print(f"{self.repo},{self.report_id} {self.title}, {desc}, {labels}")
        self.github_issue = issue.number

        # await GitHubClient.get_instance().add_issue_to_project(issue.number, is_bug=self.is_bug)

    async def setup_message(self, bot, guildID):
        if guildID == GG.GUILD:
            report_message = await bot.get_channel(TRACKER_CHAN_5ET).send(embed=self.get_embed())
        elif guildID == GG.MPMBS:
            if self.is_bug:
                report_message = await bot.get_channel(TRACKER_CHAN_MPMB_BUG).send(embed=self.get_embed())
            else:
                report_message = await bot.get_channel(TRACKER_CHAN_MPMB).send(embed=self.get_embed())
        else:
            report_message = await bot.get_channel(TRACKER_CHAN).send(embed=self.get_embed())
        self.message = report_message.id
        Report.messageIds[report_message.id] = self.report_id
        if not self.is_bug:
            await report_message.add_reaction(UPVOTE_REACTION)
            await report_message.add_reaction(DOWNVOTE_REACTION)
            await report_message.add_reaction("ℹ")

    async def commit(self):
        await self.collection.replace_one({"report_id": self.report_id}, self.to_dict(), upsert=True)

    def get_embed(self, detailed=False, ctx=None):
        embed = discord.Embed()
        if isinstance(self.reporter, int):
            embed.add_field(name="Added By", value=f"<@{self.reporter}>")
        else:
            embed.add_field(name="Added By", value=self.reporter)
        embed.add_field(name="Priority", value=PRIORITY.get(self.severity, "Unknown"))
        if not self.is_bug:
            embed.colour = 0x00ff00
            embed.add_field(name="Votes", value="\u2b06" + str(self.upvotes) + " **|** \u2b07" + str(self.downvotes))
            vote_msg = "Vote by reacting"
            if not self.github_issue:
                vote_msg += f" | {GITHUB_THRESHOLD} upvotes required to track"
            embed.set_footer(text=f"!report {self.report_id} for details or react with ℹ | {vote_msg}")
        else:
            embed.colour = 0xff0000
            embed.add_field(name="Verification", value=str(self.verification))
            embed.set_footer(
                text=f"!report {self.report_id} for details or react with ℹ| Verify with !cr/!cnr {self.report_id} [note]")

        if self.jumpUrl is not None:
            embed.add_field(name="Original Request Link", value=str(self.jumpUrl))

        embed.title = f"`{self.report_id}` {self.title}"
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
                        msg = attachment.message[:1020] or "No details."
                        embed.add_field(name=f"{VERI_EMOJI.get(attachment.veri, '')} {user}",
                                        value=msg, inline=False)
                        countAttachments += 1
            if countNotes >= 10:
                embed.description = f"*{countNotes} notes, showing first 10*"
            else:
                embed.description = f"*{countNotes} notes*"

        split = self.report_id.split("-")
        url = ""
        if split[0] == "R20":
            url = "https://cdn.discordapp.com/emojis/562116049475207178.png"
        if split[0] == "5ET":
            url = "https://images-ext-2.discordapp.net/external/8iZELuX3DXzfRIvIFX5_qHz5OdtQcOsxyiUSd3myb-g/%3Fsize%3D1024/https/cdn.discordapp.com/icons/363680385336606740/c6bfc30b26afd67e3f89c17975563488.webp"
        if split[0] == "PLUT":
            url = "https://cdn.discordapp.com/emojis/607869021731291146.png"
        if split[0] == "BUG" or split[0] == "FR":
            url = "https://images-ext-2.discordapp.net/external/cC5tnLUDKgw_urwQxMf1t7XHDGiY_zaiASVYQyIUeak/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/559331529378103317/dd8ba6c080cc25536d71a5cca75e82e4.webp"
        if split[0] == "PBUG" or split[0] == "PFR":
            url = "https://images-ext-1.discordapp.net/external/_GqRFUm-k0I0Bn_SVxrjLKDGh3Jn3QdIolw3bWsOjrg/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/574554734187380756/022b3cd708f9841e1847272cd52dbda1.webp"
        if split[0] == "DBUG" or split[0] == "DFR":
            url = "https://images-ext-2.discordapp.net/external/rWu6jSMoi6Ngejj9GcgMAC7CWRizUMZPFdvNDZ8D6Os/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/602774912595263490/3322f9c86f553dbb47f057b85a5e3d30.webp"
        if split[0] == "GBUG" or split[0] == "GFR":
            url = "https://images-ext-2.discordapp.net/external/WY_VfX_p8eL_a5_Xb1Zf1myV3lUmx2lMx_NLHFdkxKg/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/602779023151595546/f22de7baf09b8ba13135577059544895.webp"
        if split[0] == "MBUG" or split[0] == "MFR":
            url = "https://images-ext-2.discordapp.net/external/GUcJpmeQNjUMdoufIMzDJeweAAwpn7FUsc7HhmhukWw/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/534277197955989524/316c64093a82f2e428743a6e3344d8da.webp"
        embed.set_author(name=f"{self.report_id}", icon_url=url)

        return embed

    async def get_github_desc(self, ctx, serverId):
        msg = self.title
        if self.attachments:
            msg = self.attachments[0].message

        author = next((m for m in ctx.bot.get_all_members() if m.id == self.reporter), None)
        if author:
            desc = f"{msg}\n\n- {author}"
        else:
            desc = msg

        if not self.is_bug:
            i = 0
            for attachment in self.attachments[1:]:
                try:
                    if ctx.guild.id == GG.GUILD:
                        if attachment.message and i >= GITHUB_THRESHOLD_5ET:
                            continue
                    else:
                        if attachment.message and i >= GITHUB_THRESHOLD:
                            continue
                except:
                    if serverId == GG.GUILD:
                        if attachment.message and i >= GITHUB_THRESHOLD_5ET:
                            continue
                    else:
                        if attachment.message and i >= GITHUB_THRESHOLD:
                            continue
                    pass
                i += attachment.veri // 2
                msg = ''
                attachMessage = await self.get_attachment_message(ctx, attachment)
                for line in attachMessage.strip().splitlines():
                    msg += f"> {line}\n"
                desc += f"\n\n{msg}"
            desc += f"\nVotes: +{self.upvotes} / -{self.downvotes}"
        else:
            for attachment in self.attachments[1:]:
                if attachment.message:
                    continue
                msg = ''
                attachMessage = await self.get_attachment_message(ctx, attachment)
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
        if add_to_github and self.github_issue:
            if attachment.message:
                msg = await self.get_attachment_message(ctx, attachment)
                await GitHubClient.get_instance().add_issue_comment(self.repo, self.github_issue, msg)

            if attachment.veri:
                gitDesc = await self.get_github_desc(ctx, serverId)
                await GitHubClient.get_instance().edit_issue_body(self.repo, self.github_issue, gitDesc)

    async def get_attachment_message(self, ctx, attachment: Attachment):
        if isinstance(attachment.author, int):
            username = str(next((m for m in ctx.bot.get_all_members() if m.id == attachment.author), attachment.author))
        else:
            username = attachment.author

        if attachment.message is not None:
            reportIssue = await reports_to_issues(attachment.message)
            msg = f"{VERI_KEY.get(attachment.veri, '')} - {username}\n\n {reportIssue}"
        else:
            msg = f"{VERI_KEY.get(attachment.veri, '')} - {username}\n\n"
        return msg

    async def canrepro(self, author, msg, ctx, serverId):
        if [a for a in self.attachments if a.author == author and a.veri]:
            raise ReportException("You have already verified this report.")
        if not self.is_bug:
            raise ReportException("You cannot CR a feature request.")
        attachment = Attachment.cr(author, msg)
        self.verification += 1
        await self.add_attachment(ctx, serverId, attachment)
        await self.notify_subscribers(ctx, f"New CR by <@{author}>: {msg}")

    async def upvote(self, author, msg, ctx, serverId):
        if [a for a in self.attachments if a.author == author and a.veri]:
            raise ReportException("You have already either upvoted or downvoted this report.")
        if self.is_bug:
            raise ReportException("You cannot upvote a bug report.")
        attachment = Attachment.upvote(author, msg)
        self.upvotes += 1
        await self.add_attachment(ctx, serverId, attachment)
        if msg:
            await self.notify_subscribers(ctx, f"New Upvote by <@{author}>: {msg}")

        if serverId == GG.GUILD:
            if self.is_open() and not self.github_issue and self.upvotes - self.downvotes >= GITHUB_THRESHOLD_5ET:
                await self.setup_github(ctx, serverId)
        else:
            if self.is_open() and not self.github_issue and self.upvotes - self.downvotes >= GITHUB_THRESHOLD:
                await self.setup_github(ctx, serverId)

        if self.upvotes - self.downvotes in (15, 10):
            await self.update_labels()

    async def cannotrepro(self, author, msg, ctx, serverId):
        if [a for a in self.attachments if a.author == author and a.veri]:
            raise ReportException("You have already verified this report.")
        if not self.is_bug:
            raise ReportException("You cannot CNR a feature request.")
        attachment = Attachment.cnr(author, msg)
        self.verification -= 1
        await self.add_attachment(ctx, serverId, attachment)
        await self.notify_subscribers(ctx, f"New CNR by <@{author}>: {msg}")

    async def downvote(self, author, msg, ctx, serverId):
        if [a for a in self.attachments if a.author == author and a.veri]:
            raise ReportException("You have already either downvoted or upvoted this report.")
        if self.is_bug:
            raise ReportException("You cannot downvote a bug report.")
        attachment = Attachment.downvote(author, msg)
        self.downvotes += 1
        await self.add_attachment(ctx, serverId, attachment)
        if msg:
            await self.notify_subscribers(ctx, f"New downvote by <@{author}>: {msg}")
        if self.upvotes - self.downvotes in (14, 9):
            await self.update_labels()

    async def addnote(self, author, msg, ctx, serverId, add_to_github=True):
        attachment = Attachment(author, msg)
        await self.add_attachment(ctx, serverId, attachment, add_to_github)
        await self.notify_subscribers(ctx, f"New note by <@{author}>: {msg}")

    async def force_accept(self, ctx, serverId):
        await self.setup_github(ctx, serverId)

    async def force_deny(self, ctx, serverId):
        await self.notify_subscribers(ctx, f"Report closed.")
        if serverId == GG.GUILD:
            owner = GG.GIDDY
        elif serverId == GG.MPMBS:
            owner = GG.MPMB
        else:
            owner = GG.OWNER
        await self.addnote(owner, f"Resolved - This report was denied.", ctx, serverId)

        msg_ = await self.get_message(ctx, serverId)
        if msg_:
            try:
                await msg_.delete()
                if self.message in Report.message_cache:
                    del Report.message_cache[self.message]
                if self.message in Report.messageIds:
                    del Report.messageIds[self.message]
            finally:
                self.message = None

        if self.github_issue:
            await GitHubClient.get_instance().close_issue(self.repo, self.github_issue)

    def subscribe(self, ctx):
        """Ensures a user is subscribed to this report."""
        if ctx.message.author.id not in self.subscribers:
            self.subscribers.append(ctx.message.author.id)

    def unsubscribe(self, ctx):
        """Ensures a user is not subscribed to this report."""
        if ctx.message.author.id in self.subscribers:
            self.subscribers.remove(ctx.message.author.id)

    async def get_message(self, ctx, serverId):
        if self.message is None:
            return None
        elif self.message in self.message_cache:
            return self.message_cache[self.message]
        else:
            if serverId == GG.GUILD:
                msg = await ctx.bot.get_channel(TRACKER_CHAN_5ET).fetch_message(self.message)
            elif serverId == GG.MPMBS:
                if self.is_bug:
                    msg = await ctx.bot.get_channel(TRACKER_CHAN_MPMB_BUG).fetch_message(self.message)
                else:
                    msg = await ctx.bot.get_channel(TRACKER_CHAN_MPMB).fetch_message(self.message)
            else:
                try:
                    msg = await ctx.bot.get_channel(TRACKER_CHAN).fetch_message(self.message)
                except discord.HTTPException:
                    msg = None
            if msg:
                Report.message_cache[self.message] = msg
            return msg

    async def delete_message(self, ctx, serverId):
        msg_ = await self.get_message(ctx, serverId)
        if msg_:
            try:
                await msg_.delete()
                if self.message in Report.message_cache:
                    del Report.message_cache[self.message]
                if self.message in Report.messageIds:
                    del Report.messageIds[self.message]
            except discord.HTTPException:
                pass
            finally:
                self.message = None

    async def update(self, ctx, serverId):
        msg = await self.get_message(ctx, serverId)
        if msg is None and self.is_open():
            await self.setup_message(ctx.bot, serverId)
        elif self.is_open():
            await msg.edit(embed=self.get_embed())

    async def resolve(self, ctx, serverId, msg='', close_github_issue=True, pend=False, ignore_closed=False):
        if self.severity == -1 and not ignore_closed:
            raise ReportException("This report is already closed.")

        self.severity = -1
        if pend:
            await self.notify_subscribers(ctx, f"Report resolved - a patch is pending.")
        else:
            await self.notify_subscribers(ctx, f"Report closed.")
        if msg:
            await self.addnote(ctx.message.author.id, f"Resolved - {msg}", ctx, serverId)

        await self.delete_message(ctx, serverId)

        if close_github_issue and self.github_issue:
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

        if pend:
            await self.pend()

    async def unresolve(self, ctx, serverId, msg='', open_github_issue=True):
        if not self.severity == -1:
            raise ReportException("This report is still open.")

        self.severity = 6
        await self.notify_subscribers(ctx, f"Report unresolved.")
        if msg:
            await self.addnote(ctx.message.author.id, f"Unresolved - {msg}", ctx, serverId)

        await self.setup_message(ctx.bot, serverId)

        if open_github_issue and self.github_issue:
            await GitHubClient.get_instance().open_issue(self.repo, self.github_issue)

    async def untrack(self, ctx, serverId):
        await self.delete_message(ctx, serverId)
        if self.github_issue:
            await GitHubClient.get_instance().rename_issue(self.repo, self.github_issue, self.title)

        await self.collection.delete_one({"report_id": self.report_id})

    async def pend(self):
        collection = GG.MDB['PendingReports']
        await collection.insert_one(self.report_id)

    def get_labels(self):
        labels = [PRIORITY_LABELS.get(self.severity)]
        if self.is_bug:
            labels.append("bug")
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

    async def notify_subscribers(self, ctx, msg):
        msg = f"`{self.report_id}` - {self.title}: {msg}"
        for sub in self.subscribers:
            try:
                member = next(m for m in ctx.bot.get_all_members() if m.id == sub)
                await member.send(msg)
            except (StopIteration, discord.HTTPException):
                continue


async def get_next_report_num(identifier):
    collection = GG.MDB['ReportNums']
    reportNum = await collection.find_one({'key': f'{identifier}'})
    num = reportNum['amount'] + 1
    reportNum['amount'] += 1
    num = formatNumber(num)
    await collection.replace_one({"key": f'{identifier}'}, reportNum)
    return f"{num}"


def formatNumber(num):
    if num % 1 == 0:
        return int(num)
    else:
        return num


async def reports_to_issues(text):
    """
    Parses all XXX-### identifiers and adds a link to their GitHub Issue numbers.
    """

    # async def report_sub(match):
    #     #     report_id = match.group(1)
    #     #     try:
    #     #         report = await Report.from_id(report_id)
    #     #     except ReportException:
    #     #         return report_id
    #     #
    #     #     if report.github_issue:
    #     #         if report.repo:
    #     #             return f"{report_id} ({report.repo}#{report.github_issue})"
    #     #         return f"{report_id} (#{report.github_issue})"
    #     #     return report_id
    #     #
    #     # result = re.sub(r"(\w{1,}-\d{,3})", await report_sub, text)
    #     # return result
    print(f"Text: {text}")
    if text is not None:
        regex = re.findall(r"(\w{1,}-\d{,3})", text)
        for x in regex:
            report_id = x
            try:
                report = await Report.from_id(report_id)
                con = True
                if report.repo and con:
                    text = text.replace(x, f"{report_id} ({report.repo}#{report.github_issue})")
                    con = False
                if report.github_issue and con:
                    text = text.replace(x, f"{report_id} (#{report.github_issue})")
            except ReportException:
                pass
    return text


def identifier_from_repo(repo_name):
    return GG.REPO_ID_MAP.get(repo_name, 'BUG')


class ReportException(Exception):
    pass
