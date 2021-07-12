import discord.utils
from discord.ext import commands

import utils.globals as GG


def author_is_owner(ctx):
    return ctx.author.id == GG.OWNER


def _check_permissions(ctx, perms):
    if author_is_owner(ctx):
        return True

    ch = ctx.channel
    author = ctx.author
    try:
        resolved = ch.permissions_for(author)
    except AttributeError:
        resolved = None
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def _role_or_permissions(ctx, role_filter, **perms):
    if _check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if isinstance(ch, discord.abc.PrivateChannel):
        return False  # can't have roles in PMs

    try:
        role = discord.utils.find(role_filter, author.roles)
    except:
        return False
    return role is not None


def admin_or_permissions(**perms):
    def predicate(ctx):
        admin_role = "Bot Admin"
        if _role_or_permissions(ctx, lambda r: r.name.lower() == admin_role.lower(), **perms):
            return True
        raise commands.CheckFailure(
            f"You require a role named Bot Admin or these permissions to run this command: {', '.join(perms)}")

    return commands.check(predicate)


async def isManager(ctx):
    manager = await GG.MDB.Managers.find_one({"user": ctx.message.author.id, "server": ctx.guild.id})
    if manager is None:
        manager = False
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        if ctx.message.author.id == server['admin']:
            manager = True
    else:
        manager = True
    return manager


def isAssignee(ctx, report):
    if ctx.message.author.id == report.assignee:
        return True
    else:
        return False


async def isReporter(ctx, report):
    if ctx.message.author.id == report.reporter:
        guild_settings = await GG.get_settings(ctx.bot, ctx.guild.id)
        allow_selfClose = guild_settings.get("allow_selfClose", False)
        if allow_selfClose:
            return True
        else:
            return False
    else:
        return False


async def isManagerAssigneeOrReporterButton(userId, guildId, report, bot):
    manager = await GG.MDB.Managers.find_one({"user": userId, "server": guildId})
    if manager is None:
        server = await GG.MDB.Github.find_one({"server": guildId})
        if userId == server['admin']:
            return True
        elif userId == report.assignee:
            return True
        elif userId == report.reporter:
            guild_settings = await GG.get_settings(bot, guildId)
            allow_selfClose = guild_settings.get("allow_selfClose", False)
            if allow_selfClose:
                return True
            else:
                return False
        else:
            return False
    else:
        return True
