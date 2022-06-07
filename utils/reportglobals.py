import discord
from crawler_utilities.cogs.stats import track_google_analytics_event

import utils.globals as GG
from models.reports import Report

REPORTS = []


def loop(result, error):
    if error:
        raise error
    elif result:
        REPORTS.append(result)


def getAllReports():
    collection = GG.MDB['Reports']
    cursor = collection.find()
    REPORTS.clear()
    cursor.each(callback=loop)
    return REPORTS


async def finishReportCreation(self, interaction, report, reportMessage, requestChannel, bug=False):
    await report.commit()
    embed = await getAdmissionSuccessfulEmbed(self.report_id, self.author, bug, requestChannel, reportMessage)
    if self.author.dm_channel is not None:
        DM = self.author.dm_channel
    else:
        DM = await self.author.create_dm()
    try:
        await DM.send(embed=embed)
    except discord.Forbidden:
        pass
    await interaction.followup.send(f"Your submission ``{report.report_id}`` was accepted, please check your DM's for more information.\n"
                                    f"If no DM was received, you probably have it turned off, and you should check the tracker channel of the server the request was made in.", ephemeral=True)


async def finishNoteCreation(self, ctx, embed):
    if self.author.dm_channel is not None:
        DM = self.author.dm_channel
    else:
        DM = await self.author.create_dm()
    try:
        await DM.send(embed=embed)
    except discord.Forbidden:
        pass
    await ctx.interaction.followup.send(f"Your note for ``{self.report.report_id}`` was added, please check your DM's for more information.\n"
                                        f"If no DM was received, you probably have it turned off, and you should check the tracker channel of the server the request was made in.", ephemeral=True)


async def getAdmissionSuccessfulEmbed(report_id, author, bug, requestChannel, reportMessage):
    embed = discord.Embed()
    embed.title = f"Your submission ``{report_id}`` was accepted."
    if bug:
        track_google_analytics_event("Bug Report", f"{report_id}", f"{author.id}")
        embed.description = f"Your bug report was successfully posted in <#{requestChannel.id}>!"
    else:
        track_google_analytics_event("Feature Request", f"{report_id}", f"{author.id}")
        embed.description = f"Your feature request was successfully posted in <#{requestChannel.id}>!"
    embed.add_field(name="Status Checking", value=f"To check on its status: `/view {report_id}`.",
                    inline=False)
    embed.add_field(name="Note Adding",
                    value=f"To add a note: `/note {report_id} <comment>`.",
                    inline=False)
    embed.add_field(name="Subscribing",
                    value=f"To subscribe: `/subscribe {report_id}`. (This is only for others, the submitter is automatically subscribed).",
                    inline=False)
    embed.add_field(name="Voting",
                    value=f"You can find the report here: [Click me]({reportMessage.jump_url})",
                    inline=False)
    return embed


async def IdentifierDoesNotExist(ctx, identifier):
    return await ctx.interaction.respond(f"The identifier ``{identifier}`` could not be found.\n"
                                         f"If the identifier was shown in the option box, please contact the developer of the bot through the ``support`` command.\n\n"
                                         f"Otherwise this command can only be used on servers that have the feature request functionality of the bot enabled.", ephemeral=True)


async def ReportFromId(_id, ctx):
    report_id = _id.split(" | ")[0]
    guild_id = ctx.interaction.guild_id
    report = await Report.from_id(report_id, guild_id)
    return report
