import discord
from crawler_utilities.cogs.stats import track_google_analytics_event

import utils.globals as GG

UPVOTE = "Upvote"
DOWNVOTE = "Downvote"
SHRUG = "Shrug"
INFORMATION = "Info"
SUBSCRIBE = "Subscribe"
RESOLVE = "Resolve"
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
    if bug:
        track_google_analytics_event("Bug Report", f"{self.report_id}", f"{self.author.id}")
        await interaction.response.send_message(
            f"Your bug report was successfully posted in <#{requestChannel.id}>!", ephemeral=True)
    else:
        track_google_analytics_event("Feature Request", f"{self.report_id}", f"{self.author.id}")
        await interaction.response.send_message(
            f"Your feature request was successfully posted in <#{requestChannel.id}>!", ephemeral=True)

    await report.commit()
    prefix = await self.bot.get_guild_prefix(self.interaction.message)
    embed = await getAdmissionSuccessfulEmbed(self.report_id, prefix, reportMessage)
    await requestChannel.send(embed=embed)


async def getAdmissionSuccessfulEmbed(report_id, prefix, reportMessage):
    embed = discord.Embed()
    embed.title = f"Your submission ``{report_id}`` was accepted."
    embed.add_field(name="Status Checking", value=f"To check on its status: `{prefix}report {report_id}`.",
                    inline=False)
    embed.add_field(name="Note Adding",
                    value=f"To add a note: `{prefix}note {report_id} <comment>`.",
                    inline=False)
    embed.add_field(name="Subscribing",
                    value=f"To subscribe: `{prefix}subscribe {report_id}`. (This is only for others, the submitter is automatically subscribed).",
                    inline=False)
    embed.add_field(name="Voting",
                    value=f"You can find the report here: [Click me]({reportMessage.jump_url})",
                    inline=False)
    return embed