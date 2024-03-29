import asyncio

from discord import slash_command, Option, permissions, ForumChannel, InteractionResponded
from discord.ext import commands, tasks

from crawler_utilities.utils.confirmation import BotConfirmation
from modal.bug import Bug
from modal.feature import Feature
from models.questions import Question, Questionaire
from utils.autocomplete import get_server_feature_identifiers, get_server_identifiers, get_server_bug_identifiers
from utils.checks import is_manager
from utils.ticketglobals import identifier_does_not_exist
from utils import globals as GG

log = GG.log


class CreateTicket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.get_identifiers.start()
        self.userCache = set()

    @tasks.loop(hours=1)
    async def get_identifiers(self):
        await self.bot.wait_until_ready()
        log.info("[IN-MEMORY] Reloading Identifiers")
        await GG.cache_identifiers()
        await GG.cache_server_channels()
        log.info("[IN-MEMORY] Done Reloading Identifiers")

    @slash_command(name="questionnaire")
    @permissions.guild_only()
    async def slash_questionnaire(self, ctx,
                                  identifier: Option(str, "For what identifier do you want to add questions?", autocomplete=get_server_identifiers),
                                  position: Option(int, "In what position? (Between 1 and 5)", min_value=1, max_value=5),
                                  required: Option(bool, "Is the question required?"),
                                  style: Option(str, "What input style?", choices=["Singleline", "Multiline"]),
                                  label: Option(str, "What's the question?"),
                                  placeholder: Option(str, "Optional text inside the input box. (Max 100 characters.)", default="")
                                  ):
        """Create questions for feature requests, bugs, and support tickets."""
        if not await is_manager(ctx):
            return await ctx.respond("You do not have the required permissions to use this command.", ephemeral=True)

        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                identifier = iden['identifier']
                exists = True

        if not exists:
            return await identifier_does_not_exist(ctx, identifier)

        if style == "Singleline":
            style = 1
        else:
            style = 2

        question = Question(position - 1, label, placeholder, style, required)

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        if questionaire is None:
            questionaire = Questionaire(ctx.interaction.guild_id, identifier)

        duplicate = await questionaire.add_question(question)
        if duplicate is False:
            confirmation = BotConfirmation(ctx, 0x012345)
            try:
                channel = await self.bot.fetch_channel(ctx.interaction.channel_id)
            except Exception:
                return await ctx.respond(f"I tried posting a confirmation box in this channel, but I don't have access to this channel\nPlease try it in a channel where I have send message permissions.", ephemeral=True)
            await ctx.defer(ephemeral=True)
            await confirmation.confirm(f"A question in this position already exists, do you want to overwrite it?", channel=channel)
            if confirmation.confirmed:
                await confirmation.update(f"Confirmed, overwriting question..", color=0x55ff55)
                await asyncio.sleep(2)
                await confirmation.quit()
                await questionaire.add_question(question, True)
                await ctx.respond(f"Question ``{label}`` added for ``{identifier}``", ephemeral=True)
            else:
                await confirmation.quit()
                await ctx.respond("Question wasn't added.", ephemeral=True)
        else:
            await ctx.respond(f"Question ``{label}`` added for ``{identifier}``", ephemeral=True)

    @slash_command(name="featurerequest")
    @permissions.guild_only()
    async def slash_featurerequest(self, ctx, identifier: Option(str, "For what identifier do you want to make a feature request?", autocomplete=get_server_feature_identifiers)):
        """Opens a modal to post a feature request."""
        exists = False
        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                identifier = iden['identifier']
                repo = iden['repo']
                tracker = iden['tracker']
                channel = iden['channel']
                if iden['type'] == "feature":
                    exists = True

        if not exists:
            return await identifier_does_not_exist(ctx, identifier)

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        modal = Feature(identifier, self.bot, ctx.interaction, ctx.interaction.user, repo, tracker, channel, questionaire)
        await ctx.interaction.response.send_modal(modal)

    @slash_command(name="bugreport")
    @permissions.guild_only()
    async def slash_bug(self, ctx, identifier: Option(str, "For what identifier do you want to make a bug ticket?", autocomplete=get_server_bug_identifiers)):
        """Opens a modal to post a bug."""
        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                identifier = iden['identifier']
                repo = iden['repo']
                tracker = iden['tracker']
                channel = iden['channel']
                if iden['type'] == "bug":
                    exists = True

        if not exists:
            return await identifier_does_not_exist(ctx, identifier)

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        modal = Bug(identifier, self.bot, ctx.interaction, ctx.interaction.user, repo, tracker, channel, questionaire)
        await ctx.interaction.response.send_modal(modal)

    @slash_command(name="supportrequest")
    @permissions.guild_only()
    async def slash_support(self, ctx, identifier: Option(str, "For what identifier do you want to make a support request?", autocomplete=get_server_bug_identifiers)):
        """Opens a modal to post a support request."""
        exists = False

        server = await GG.MDB.Github.find_one({"server": ctx.interaction.guild_id})
        for iden in server['listen']:
            if iden['identifier'] == identifier or iden.get('alias', '') == identifier:
                identifier = iden['identifier']
                repo = iden['repo']
                tracker = iden['tracker']
                channel = iden['channel']
                if iden['type'] == "bug":
                    exists = True

        if not exists:
            return await identifier_does_not_exist(ctx, identifier)

        questionaire = await Questionaire.from_id(identifier, ctx.interaction.guild_id)
        modal = Bug(identifier, self.bot, ctx.interaction, ctx.interaction.user, repo, tracker, channel, questionaire)
        await ctx.interaction.response.send_modal(modal)


def setup(bot):
    log.info("[Ticket] CreateTicket...")
    bot.add_cog(CreateTicket(bot))
