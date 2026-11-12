# GithubCrawler

## Repairing rounded Discord IDs

JavaScript numbers cannot represent all Discord snowflakes exactly. Do not edit
IDs as ordinary JavaScript numbers in a MongoDB GUI; use its BSON Int64 or
Extended JSON long type instead. Stop any external process that may rewrite IDs,
and take a MongoDB backup before repairing data.

After deploying and restarting the bot, the server owner or bot owner can run
`/issue repair-ids` in the affected server. It fetches that server's channels
from Discord and compares IDs against the bot's connected guilds and those
channels. The ephemeral response contains a text file listing each proposed
change and unresolved items. Review every rounded match against Discord before
running `/issue repair-ids approval:<token>` with the preview's token. The
token is valid only for the same freshly computed plan. Repeat per server.

The repair covers guild IDs in `Github`, `Managers`, `TicketNums`, `questions`,
`issuesettings`, `prefixes`, and `Tickets.server_id`, plus `Github.listen`
channel/tracker IDs and `Tickets.trackerId` for tickets scoped to this server.
It converts IDs to the types expected by those collections. It does not repair
user, message, thread, embedded URL, or other unknown IDs. Legacy tickets
without `server_id` whose tracker matches a visible channel are reported but
not changed; other unscoped tickets may not be identifiable. Ambiguous or
unavailable channel IDs are also reported but not changed. Deleted or
inaccessible Discord objects cannot be reliably matched.

A rounded value may match multiple original snowflakes even if only one object
is currently visible, so a proposed rounded match is not proof of identity.
Conflicting guild configurations are refused; database writes are checked for
concurrent edits but are not transactional. If a repair stops partway through,
review a new preview and retry, or restore the backup. The bot refreshes its
caches after applying changes.

