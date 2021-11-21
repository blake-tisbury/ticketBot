import asyncio
import math

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
import json
import asyncio
from dotenv import load_dotenv
import os
from discord_components import *
import time

path = 'token.env'
prefix = '$'
embedTitle = '⚠ Ticket Update'
ticket_channel = 865315043629334569
avg_wait = 30
timeout_time = (30 * 60)  # time to wait for a response in seconds

load_dotenv(dotenv_path=path, verbose=True)
TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix=f'{prefix}')
bot.remove_command("help")


# algorithm for calculating average wait time of tickets
async def calc_wait():
    current_time = time.localtime()
    hour = int(time.strftime("%H", current_time))
    minute = int(time.strftime("%M", current_time))
    x = hour + (minute / 60)
    v = ((.25 * math.sin((x - 10.6) / 4.1)) + .75)
    r = avg_wait / v
    return r


# updates the bot description to show calculated wait time
async def wait_update():
    description = ('▪Tickets are a way to speak with staff directly in an organized'
                   ' manner. \n▪Press the button below to create your own ticket. \n \n⌛ Current response time is '
                   f'around **{int(await calc_wait())}** minutes. ⌛')
    embed = discord.Embed(title="🏷️  What's a ticket?", description=description, color=0xcd72df)
    embed.set_footer(text='TheaLater Ticket Bot ✨')

    msg = await bot.get_channel(ticket_channel).send(
        embed=embed,
        components=
        [Button(emoji="📩", label="Create Ticket")])

    while True:
        await asyncio.sleep(60)

        description = ('▪Tickets are a way to speak with staff directly in an organized'
                       ' manner. \n▪Press the button below to create your own ticket. \n \n⌛ Current response time is '
                       f'around **{int(await calc_wait())}** minutes. ⌛')
        embed = discord.Embed(title="🏷️  What's a ticket?", description=description, color=0xcd72df)
        embed.set_footer(text='TheaLater Ticket Bot ✨')

        await msg.edit(
            embed=embed,
            components=
            [Button(emoji="📩", label="Create Ticket")])
        await msg.edit(embed=embed)


@bot.event
async def on_ready():
    DiscordComponents(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(wait_update())

    print("Bot running with:")
    print("Username: ", bot.user.name)
    print("User ID: ", bot.user.id)


# handles user input
@bot.event
async def on_button_click(interaction):
    if interaction.channel.id == ticket_channel:
        if interaction.responded:
            return
        else:
            loop = asyncio.get_event_loop()
            loop.create_task(new(interaction.user, interaction.channel, interaction))

    else:
        await closeTicket(interaction.channel)


# Starting Ticket Message
@bot.command()
async def new(user, channel, controller, args=None):
    await bot.wait_until_ready()

    def check(message):
        return message.author == user and message.channel == ticket_channel

    responses = []

    if args == None:
        message_content = "▪ Hi there! I'm a bot! Please tell us about your issue so we can better assist you." \
                          "\n ""\n ▪ If you opened this ticket by accident or wish to close it, press the red button."

    else:
        message_content = "".join(args)

    with open("data.json") as f:
        data = json.load(f)

    ticket_number = int(data["ticket-counter"])
    ticket_number += 1

    if f"ticket-{str(user.name).lower()}" not in data["ticket-channel"]:
        ticket_channel = await channel.guild.create_text_channel("ticket-{}".format(user.name))
        print(f'New ticket created for {interaction.User.name}')

        data["ticket-channel"].append(str(ticket_channel))
        data["ticket-channel-ids"].append(ticket_channel.id)

        await ticket_channel.set_permissions(channel.guild.get_role(channel.guild.id), send_messages=False,
                                             read_messages=False)
        for role_id in data["valid-roles"]:
            role = channel.guild.get_role(role_id)

            await ticket_channel.set_permissions(role, send_messages=True, read_messages=True, add_reactions=True,
                                                 embed_links=True, attach_files=True, read_message_history=True,
                                                 external_emojis=True)

        await ticket_channel.set_permissions(user, send_messages=True, read_messages=True, add_reactions=True,
                                             embed_links=True, attach_files=True, read_message_history=True,
                                             external_emojis=True)

        em = discord.Embed(title="New ticket from {}#{}".format(user.name, user.discriminator),
                           description="{}".format(message_content), color=0x00a8ff)
        em.set_footer(text='TheaLater Ticket Bot ✨')

        data["ticket-counter"] = int(ticket_number)
        with open("data.json", 'w') as f:
            json.dump(data, f)

        await bot.get_channel(ticket_channel.id).send(
            embed=em,
            components=[
                Button(emoji="📩", label="Close Ticket", style=4),
            ]
        )

        created_em = discord.Embed(title='🏷️  Ticket Created!',
                                   description="Your ticket has been created at {}".format(ticket_channel.mention),
                                   color=0x00a8ff)
        created_em.set_footer(text='TheaLater Ticket Bot ✨')
        await user.send(embed=created_em)

        description = f"Your ticket has been created at {ticket_channel.mention}"
        embed = discord.Embed(title="🏷️  Ticket Created!", description=description, color=0xcd72df)
        await controller.respond(embed=embed)
        ticket_channel_name = str(f'ticket-{controller.user.name}').lower()
        channel_type = discord.utils.get(controller.guild.channels, name=ticket_channel_name)

        try:
            msg = await bot.wait_for('message', check=check, timeout=timeout_time)

            response = msg.content
            responses.append(response)

        except asyncio.TimeoutError:
            await closeTicket(channel_type)
            await sendTimeout(user)
        try:
            while True:
                msg = await bot.wait_for('message', check=check, timeout=86400)

                response = msg.content
                responses.append(response)

        except asyncio.TimeoutError:
            await closeTicket(channel)
            await sendTimeoutDay(user)
    else:
        ticket_channel_name = str(f'ticket-{controller.user.name}').lower()
        channel_type = discord.utils.get(controller.guild.channels, name=ticket_channel_name)

        description = f"You already have an open ticket, if you would like to create a new one, close your old one at {channel_type.mention} "
        embed = discord.Embed(title="⛔ Active ticket", description=description, color=0xcd72df)
        await controller.respond(embed=embed)


@bot.command()
async def closeTicket(channel):
    with open("data.json") as f:
        data = json.load(f)

    channel_name = channel.name
    channel_type = channel

    channel_id = channel_type.id

    channel_type = bot.get_channel(channel_id)

    if channel.id in data["ticket-channel-ids"]:
        try:

            indexID = data["ticket-channel-ids"].index(int(channel_id))
            del data["ticket-channel-ids"][indexID]

            index = data["ticket-channel"].index(str(channel_name))
            del data["ticket-channel"][index]

            with open('data.json', 'w') as f:
                json.dump(data, f)

            await channel_type.delete()
        except asyncio.TimeoutError:
            em = discord.Embed(title=embedTitle,
                               description="You have run out of time to close this ticket. Please run the command again.",
                               color=0x00a8ff)
            await channel_type.send(embed=em)


# closes the ticket automatically if the user hasn't typed anything yet
@bot.command()
async def sendTimeout(user):
    created_em = discord.Embed(title='⚠ Ticket Update',
                               description="It looks like you haven't typed anything in your ticket, did you open one "
                                           "by accident? Since this is probably the case, I will go ahead and close "
                                           "the ticket for you. Remember, you can always open a new one if need be!",
                               color=0x00a8ff)
    created_em.set_footer(text='TheaLater Ticket Bot ✨')

    await user.send(embed=created_em)


# closes the ticket if the user is unresponsive for a large amount of time
@bot.command()
async def sendTimeoutDay(user):
    created_em = discord.Embed(title='⚠ Ticket Update',
                               description="We haven't heard from you in a while so we are closing this ticket for "
                                           "you. Remember, you can always open a new ticket if need be!",
                               color=0x00a8ff)
    created_em.set_footer(text='TheaLater Ticket Bot ✨')

    await user.send(embed=created_em)


# defines help command, shows useful bot info
@bot.command()
async def help(ctx):
    with open("data.json") as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if ctx.author.guild_permissions.administrator or valid_user:

        em = discord.Embed(title="Ticket Bot Commands", description="", color=0x00a8ff)
        em.add_field(name=f"`{prefix}new <message>`",
                     value="This creates a new ticket. Add any words after the command if you'd like to send a "
                           "message when we initially create your ticket.")
        em.add_field(name=f"`{prefix}close`",
                     value="Use this to close a ticket. This command only works in ticket channels.")
        em.add_field(name=f"`{prefix}addaccess <role_id>`",
                     value="This can be used to give a specific role access to all tickets. This command can only be run if you have an admin-level role for this bot.")
        em.add_field(name=f"`{prefix}delaccess <role_id>`",
                     value="This can be used to remove a specific role's access to all tickets. This command can only be run if you have an admin-level role for this bot.")

        await ctx.send(embed=em)

        em = discord.Embed(title="Useful Bot Info", description="", color=0x00a8ff)
        em.add_field(name=f"`Ticket Timeouts`",
                     value="New tickets will close after 30 minutes of inactivity. However, after every message this "
                           "timer is reset to one day. After a full day of ticket inactivity, the ticket will be "
                           "closed and the channel will be deleted")
        em.add_field(name="`Estimated Wait Time`",
                     value="The estimated wait time is calculated by a sine wave modeled after our player count. "
                           "Meaning that during peak times (when staff is more active) the response wait times will "
                           "be shorter. The range of response time is 30-60 minutes.")
        em.add_field(name="`Duplicate Tickets`",
                     value="No user is allowed to have more than one ticket at a time, so if they wish to create "
                           "another one, they will have to close their previous ticket. An error message will prompt "
                           "the user upon ticket creation if they already have a ticket")
        em.set_footer(text="em and caroline bullied me into this - tisbury")

        await ctx.send(embed=em)
    else:

        em = discord.Embed(title="Support Bot Help", description="", color=0x00a8ff)
        em.add_field(name=f"`{prefix}new <message>`",
                     value="This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket.")
        em.add_field(name=f"`{prefix}close`",
                     value="Use this to close a ticket. This command only works in ticket channels.")
        em.set_footer(text="Tisbury")

        await ctx.send(embed=em)


# Close Ticket Command
@bot.command()
async def close(ctx):
    with open('data.json') as f:
        data = json.load(f)

    if ctx.channel.id in data["ticket-channel-ids"]:

        channel_id = ctx.channel.id
        channel_name = ctx.channel.name

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "close"

        try:

            em = discord.Embed(title=embedTitle,
                               description="Are you sure you want to close this ticket? Reply with `close` if you are sure.",
                               color=0x00a8ff)

            await ctx.send(embed=em)
            await bot.wait_for('message', check=check, timeout=60)
            await ctx.channel.delete()

            indexID = data["ticket-channel-ids"].index(channel_id)
            del data["ticket-channel-ids"][indexID]

            index = data["ticket-channel"].index(channel_name)
            del data["ticket-channel"][index]

            with open('data.json', 'w') as f:
                json.dump(data, f)

        except asyncio.TimeoutError:
            em = discord.Embed(title=embedTitle,
                               description="You have run out of time to close this ticket. Please run the command "
                                           "again.",
                               color=0x00a8ff)
            await ctx.send(embed=em)


# command for adding certain users to a ticket
@bot.command()
async def addaccess(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:
        role_id = int(role_id)

        if role_id not in data["valid-roles"]:

            try:
                role = ctx.guild.get_role(role_id)

                with open("data.json") as f:
                    data = json.load(f)

                data["valid-roles"].append(role_id)

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title=embedTitle,
                                   description="You have successfully added `{}` to the list of roles with access to tickets.".format(
                                       role.name), color=0x00a8ff)

                await ctx.send(embed=em)

            except:
                em = discord.Embed(title=embedTitle,
                                   description="That isn't a valid role ID. Please try again with a valid role ID.")
                await ctx.send(embed=em)

        else:
            em = discord.Embed(title=embedTitle, description="That role already has access to tickets!",
                               color=0x00a8ff)
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title=embedTitle, description="Sorry, you don't have permission to run that command.",
                           color=0x00a8ff)
        await ctx.send(embed=em)


# removes access to ticket
@bot.command()
async def delaccess(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:

        try:
            role_id = int(role_id)
            role = ctx.guild.get_role(role_id)

            with open("data.json") as f:
                data = json.load(f)

            valid_roles = data["valid-roles"]

            if role_id in valid_roles:
                index = valid_roles.index(role_id)

                del valid_roles[index]

                data["valid-roles"] = valid_roles

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title=embedTitle,
                                   description="You have successfully removed `{}` from the list of roles with access "
                                               "to tickets.".format(
                                       role.name), color=0x00a8ff)

                await ctx.send(embed=em)

            else:

                em = discord.Embed(title=embedTitle,
                                   description="That role already doesn't have access to tickets!", color=0x00a8ff)
                await ctx.send(embed=em)

        except:
            em = discord.Embed(title=embedTitle,
                               description="That isn't a valid role ID. Please try again with a valid role ID.")
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title=embedTitle, description="Sorry, you don't have permission to run that command.",
                           color=0x00a8ff)
        await ctx.send(embed=em)


if __name__ == '__main__':
    bot.run(TOKEN)
