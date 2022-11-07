import discord.utils
from discord.ext import commands

import utils.globals as GG
from utils.functions import get_settings


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


async def is_manager(ctx, ticket=None):
    manager = await GG.MDB.Managers.find({"user": ctx.interaction.user.id, "server": ctx.guild.id}).to_list(length=None)
    if len(manager) == 0:
        server = await GG.MDB.Github.find_one({"server": ctx.guild.id})
        if ctx.interaction.user.id == server['admin']:
            return True
        return False
    else:
        for man in manager:
            identifier = man.get('identifier', None)
            if ticket is not None and identifier in ticket.ticket_id.lower():
                return True
            if identifier is None:
                return True
        return False


def is_assignee(ctx, ticket):
    if ctx.interaction.user.id == ticket.assignee:
        return True
    else:
        return False


async def is_creator(ctx, ticket):
    if ctx.interaction.user.id == ticket.reporter:
        guild_settings = await get_settings(ctx.bot, ctx.interaction.guild_id)
        allow_selfClose = guild_settings.get("allow_selfClose", False)
        if allow_selfClose:
            return True
        else:
            return False
    else:
        return False


async def is_manager_assignee_or_creator(userId, guildId, ticket, bot):
    manager = await GG.MDB.Managers.find({"user": userId, "server": guildId}).to_list(length=None)
    print(manager)
    if len(manager) == 0:
        print("manager is none")
        server = await GG.MDB.Github.find_one({"server": guildId})
        print(server)
        if userId == server['admin']:
            print("user is admin")
            return True
        elif userId == ticket.assignee:
            print("user is assignee")
            return True
        elif userId == ticket.reporter:
            print("user is reporter")
            guild_settings = await get_settings(bot, guildId)
            allow_selfClose = guild_settings.get("allow_selfClose", False)
            if allow_selfClose:
                return True
            return False
        else:
            return False
    else:
        for man in manager:
            identifier = man.get('identifier', None)
            print(identifier)
            print("ticket_id: ", ticket.ticket_id.lower())
            if identifier is None:
                return True
            else:
                if ticket is not None and identifier in ticket.ticket_id.lower():
                    return True
                else:
                    return False
        return False
