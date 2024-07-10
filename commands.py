import datetime
from bot_setup import bot, bucharest_timezone
from config import OPENWEATHERMAP_API_KEY
import re
from typing import List
import nextcord
from nextcord import Interaction
import aiohttp
import asyncio
import io
import random
import imghdr
from PIL import Image

@bot.slash_command(name="hello", description="Says hello to the user")
async def hello(interaction: nextcord.Interaction):
    await interaction.response.send_message("Hello! 👋")

@bot.slash_command(name="delete", description="Delete a message by its ID")
async def delete(ctx: nextcord.Interaction, message_id: str):
    # Retrieve the user ID associated with the interaction
    user_id = ctx.user.id

    # Retrieve the member associated with the interaction
    member = ctx.guild.get_member(user_id)

    # Check if the member can manage messages
    if member.guild_permissions.manage_messages:
        # Extract the message ID from the input
        message_id = message_id.strip().split()[-1]

        try:
            message_id = int(message_id)  # Attempt to cast to an integer
        except ValueError:
            await ctx.send("Please provide a valid integer for the message ID.")
            return

        try:
            # Delete the message by ID
            message = await ctx.channel.fetch_message(message_id)

            # Send confirmation message
            await ctx.send(f"The message has been deleted.")

            # Access message logs channel (adjust channel name accordingly)
            log_channel = nextcord.utils.get(message.guild.channels, name="message-logs")

            if log_channel:
                try:
                    # Create embed message for event log
                    embed = nextcord.Embed(description=f"Message deleted in {message.channel.mention}", color=nextcord.Color.red())
                    embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
                    if message.content:  # Check if message content exists before adding it to the embed
                        embed.add_field(name="Content", value=message.content, inline=False)
                    else:
                        embed.add_field(name="Content", value="*(Message content was empty)*", inline=False)
                    bucharest_time = message.created_at.astimezone(bucharest_timezone)
                    bucharest_time_formatted = bucharest_time.strftime("%B %d, %Y at %I:%M %p")
                    embed.set_footer(text=f"User ID: {message.author.id} • {bucharest_time_formatted}")

                    await log_channel.send(embed=embed)
                except Exception as e:
                    print(f"An error occurred while sending the delete message to the log channel: {e}")

            # Delete the message after potential logging error
            await message.delete()

        except nextcord.NotFound:
            await ctx.send("Message not found.")
        except nextcord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
    else:
        await ctx.send("You do not have the required permissions to use this command.")

@bot.slash_command(name="purge", description="Delete multiple messages")
async def purge(ctx: nextcord.Interaction, amount: int):
    # Retrieve the member associated with the interaction
    member = ctx.guild.get_member(ctx.user.id)
    
    # Check if the member has administrator permissions
    if not member.guild_permissions.administrator:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    if amount < 2:
        await ctx.send("Purge 2 or more messages.")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount)
        
        log_channel = nextcord.utils.get(ctx.guild.channels, name="message-logs")  # Adjust channel name accordingly
        
        # Create a text file containing purged messages
        file_content = ""
        deleted_sorted = sorted(deleted, key=lambda m: m.created_at)
        for message in deleted_sorted:
            bucharest_time = message.created_at.astimezone(bucharest_timezone)
            bucharest_time_formatted = bucharest_time.strftime("%B %d, %Y at %I:%M %p")
            file_content += f"{message.author.display_name}: {message.content}; {bucharest_time_formatted}\n"

        with io.BytesIO(file_content.encode()) as log_file:
            # Upload the file to the message logs channel
            file_msg = await log_channel.send(file=nextcord.File(log_file, filename="purged_messages.txt"))
            file_url = file_msg.attachments[0].url
        
        log_embed = nextcord.Embed(title="Message Purge Log", description=f"{len(deleted)} messages have been deleted in {ctx.channel.mention}", color=0xff0000)
        
        await log_channel.send(embed=log_embed)

        await ctx.send(f"{len(deleted)} messages have been deleted.")

    except nextcord.Forbidden:
        await ctx.send("I don't have permission to delete messages.")

@bot.slash_command(name="create_category", description="Create a new category")
async def create_category(ctx: nextcord.Interaction, category_name: str):
    try:
        # Retrieve the member associated with the interaction
        member = ctx.guild.get_member(ctx.user.id)
        
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return

        guild = ctx.guild
        existing_category = nextcord.utils.get(guild.categories, name=category_name)
        if existing_category:
            await ctx.send(f"A category with the name {category_name} already exists.")
            return
        else:
            await guild.create_category(category_name)
            await ctx.send(f"Category {category_name} has been created.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="edit_category_name", description="Edit the name of a category")
async def edit_category_name(ctx: nextcord.Interaction, old_name: str, new_name: str):
    try:
        # Retrieve the member associated with the interaction
        member = ctx.guild.get_member(ctx.user.id)
        
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=old_name)
        if category:
            await category.edit(name=new_name)
            await ctx.send(f"Category name has been changed from {old_name} to {new_name}.")
        else:
            await ctx.send(f"No category with the name {old_name} found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_category", description="Delete a category")
async def delete_category(ctx: nextcord.Interaction, category_name: str):
    try:
        # Retrieve the member associated with the interaction
        member = ctx.guild.get_member(ctx.user.id)
        
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        # Find the category with the specified name
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        
        if category:
            # Check if there are multiple categories with the same name
            categories = [cat for cat in ctx.guild.categories if cat.name == category_name]
            if len(categories) > 1:
                await ctx.send(f"Multiple categories with the name '{category_name}' found. Please specify the category ID.")
                return
            
            # Delete the category
            await category.delete()
            await ctx.send(f"Category '{category_name}' has been deleted.")
        else:
            await ctx.send(f"No category with the name '{category_name}' found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="create_text_channel", description="Create a new text channel")
async def create_text_channel(ctx: nextcord.Interaction, category_name: str, channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        guild = ctx.guild
        category = nextcord.utils.get(guild.categories, name=category_name)
        
        if category:
            # Check if a channel with the same name already exists within the category
            existing_channel = nextcord.utils.get(category.text_channels, name=channel_name)
            if existing_channel:
                await ctx.send(f"A text channel with the name '{channel_name}' already exists in the category '{category_name}'.")
            else:
                await guild.create_text_channel(channel_name, category=category)
                await ctx.send(f"Channel '{channel_name}' has been created under category '{category_name}'.")
        else:
            await ctx.send(f"No category with the name '{category_name}' found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}") 

@bot.slash_command(name="edit_text_channel_name", description="Edit the name of a channel")
async def edit_channel_name(ctx: nextcord.Interaction, category_name: str, old_name: str, new_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if category:
            # Check if the old channel name exists within the category
            channel = nextcord.utils.get(category.text_channels, name=old_name)
            if channel:
                # Check if the new name already exists within the category
                existing_channel = nextcord.utils.get(category.text_channels, name=new_name)
                if existing_channel:
                    await ctx.send(f"A text channel with the name '{new_name}' already exists in the category '{category_name}'.")
                else:
                    # Rename the channel
                    await channel.edit(name=new_name)
                    await ctx.send(f"Channel name has been changed from '{old_name}' to '{new_name}' in the category '{category_name}'.")
            else:
                await ctx.send(f"No text channel with the name '{old_name}' found in the category '{category_name}'.")
        else:
            await ctx.send(f"No category with the name '{category_name}' found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="edit_channel_topic", description="Edit the topic of a channel")
async def edit_channel_topic(ctx: nextcord.Interaction, category_name: str, channel_name: str, new_topic: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if category:
            channel = nextcord.utils.get(category.text_channels, name=channel_name)  # Checking if it's a text channel
            if channel:
                await channel.edit(topic=new_topic)
                await ctx.send(f"Channel topic has been changed to '{new_topic}' in the category {category_name}.")
            else:
                await ctx.send(f"No text channel with the name {channel_name} found in the category {category_name}.")
        else:
            await ctx.send(f"No category with the name {category_name} found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_channel_topic", description="Delete the topic of a channel")
async def delete_channel_topic(ctx: nextcord.Interaction, category_name: str, channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if category:
            channel = nextcord.utils.get(category.text_channels, name=channel_name)  # Checking if it's a text channel
            if channel:
                await channel.edit(topic="")
                await ctx.send(f"Channel topic has been deleted for {channel_name} in the category {category_name}.")
            else:
                await ctx.send(f"No text channel with the name {channel_name} found in the category {category_name}.")
        else:
            await ctx.send(f"No category with the name {category_name} found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_text_channel", description="Delete a channel")
async def delete_channel(ctx: nextcord.Interaction, category_name: str, channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member can manage channels
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if category:
            channel = nextcord.utils.get(category.text_channels, name=channel_name)  # Checking if it's a text channel
            if channel:
                await channel.delete()
                await ctx.send(f"Channel {channel_name} has been deleted from the category {category_name}.")
            else:
                await ctx.send(f"No text channel with the name {channel_name} found in the category {category_name}.")
        else:
            await ctx.send(f"No category with the name {category_name} found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="duplicate_channel", description="Duplicate a channel")
async def duplicate_channel(ctx: nextcord.Interaction, channel_name: str, new_channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.manage_channels:
            await ctx.send("You do not have the required permissions to use this command.")
            return

        channel = nextcord.utils.get(ctx.guild.channels, name=channel_name)
        if not channel:
            await ctx.send(f"No channel with the name '{channel_name}' found.")
            return

        category = channel.category
        if not category:
            await ctx.send("The channel must be within a category to duplicate.")
            return

        # Duplicate the channel
        new_channel = await channel.clone(name=new_channel_name, category=category)
        await ctx.send(f"Channel '{channel_name}' duplicated as '{new_channel_name}'.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="move_channel_to_category", description="Move a channel to a different category")
async def move_channel_to_category(ctx: nextcord.Interaction, channel_name: str, category_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        channel = nextcord.utils.get(ctx.guild.channels, name=channel_name)
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        
        # Find all channels with the same name as the given channel name
        channels_with_same_name = [ch for ch in ctx.guild.channels if ch.name == channel_name]
        
        if channel and category:
            if len(channels_with_same_name) > 1:
                old_category_name = channel.category.name if channel.category else "None"
                await ctx.send(f"Multiple channels found with the name '{channel_name}'. Please specify the channel ID or mention the channel.")
            else:
                old_category_name = channel.category.name if channel.category else "None"
                await channel.edit(category=category)
                await ctx.send(f"Channel '{channel_name}' moved from category '{old_category_name}' to category '{category_name}'.")
        else:
            await ctx.send(f"Channel '{channel_name}' or category '{category_name}' not found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="list_channels_in_category", description="List channels in a category")
async def list_channels_in_category(ctx: nextcord.Interaction, category_name: str):
    category = nextcord.utils.get(ctx.guild.categories, name=category_name)
    if category:
        channels = category.channels
        channel_list = "\n".join(channel.name for channel in channels)
        await ctx.send(f"Channels in category '{category_name}':\n{channel_list}")
    else:
        await ctx.send(f"No category with the name '{category_name}' found.")

@bot.slash_command(name="allow_category_permissions", description="Allow a role to perform various actions in a category")
async def allow_category_permissions(ctx: nextcord.Interaction, category_name: str, role_name: str, permissions: str):
    try:
        await manage_category_permissions(ctx, category_name, role_name, permissions.split(','), allow=True)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="revoke_category_permissions", description="Revoke a role's permissions for various actions in a category")
async def revoke_category_permissions(ctx: nextcord.Interaction, category_name: str, role_name: str, permissions: str):
    try:
        await manage_category_permissions(ctx, category_name, role_name, permissions.split(','), allow=False)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

async def manage_category_permissions(ctx: nextcord.Interaction, category_name: str, role_name: str, permissions: List[str], allow: bool):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if not category:
            await ctx.send(f"No category with the name '{category_name}' found.")
            return
        
        role = nextcord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"No role with the name '{role_name}' found.")
            return
        
        for channel in category.channels:
            overwrite = channel.overwrites_for(role)
            for permission in permissions:
                if hasattr(overwrite, permission):
                    setattr(overwrite, permission, allow)
                else:
                    await ctx.send(f"Invalid permission '{permission}'.")
                    return
            await channel.set_permissions(role, overwrite=overwrite)

        permission_actions = "allowed" if allow else "revoked"
        permissions_text = ", ".join(permission.replace("_", " ") for permission in permissions)
        await ctx.send(f"Role '{role_name}' permissions for {permissions_text} in category '{category_name}' have been {permission_actions}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="allow_permissions", description="Allow a role to perform various actions in a channel")
async def allow_permissions(ctx: nextcord.Interaction, category_name: str, channel_name: str, role_name: str, permissions: str):
    try:
        await manage_channel_permissions(ctx, category_name, channel_name, role_name, permissions.split(','), allow=True)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="revoke_permissions", description="Revoke a role's permissions for various actions in a channel")
async def revoke_permissions(ctx: nextcord.Interaction, category_name: str, channel_name: str, role_name: str, permissions: str):
    try:
        await manage_channel_permissions(ctx, category_name, channel_name, role_name, permissions.split(','), allow=False)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

PERMISSIONS = [
    "send_messages",
    "add_reactions",
    "manage_channels",
    "create_invite",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
    "embed_links",
    "attach_files",
    "use_external_emojis",
    "mention_everyone",
    "manage_messages",
    "manage_threads",
    "read_message_history",
    "send_tts_messages",
    "use_slash_commands",
    "send_voice_messages",
    "use_activities"
]

async def manage_channel_permissions(ctx: nextcord.Interaction, category_name: str, channel_name: str, role_name: str, permissions: List[str], allow: bool):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if not category:
            await ctx.send(f"No category with the name '{category_name}' found.")
            return
        
        channel = nextcord.utils.get(category.channels, name=channel_name)
        if not channel:
            await ctx.send(f"No channel with the name '{channel_name}' found in category '{category_name}'.")
            return
        
        role = nextcord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"No role with the name '{role_name}' found.")
            return
        
        overwrite = nextcord.PermissionOverwrite()
        for permission in permissions:
            if hasattr(overwrite, permission):
                setattr(overwrite, permission, allow)
            else:
                await ctx.send(f"Invalid permission '{permission}'.")
                return
        
        await channel.set_permissions(role, overwrite=overwrite)

        permission_actions = "allowed" if allow else "revoked"
        permissions_text = ", ".join(permission.replace("_", " ") for permission in permissions)
        await ctx.send(f"Role '{role_name}' permissions for {permissions_text} in channel '{channel_name}' under category '{category_name}' have been {permission_actions}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="allow_role_permissions", description="Allow a role to perform various actions on the server")
async def allow_permissions(ctx: nextcord.Interaction, role_name: str, permissions: str):
    try:
        await manage_role_permissions(ctx, role_name, permissions, allow=True)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="revoke_role_permissions", description="Revoke a role's permissions for various actions on the server")
async def revoke_permissions(ctx: nextcord.Interaction, role_name: str, permissions: str):
    try:
        await manage_role_permissions(ctx, role_name, permissions, allow=False)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

ALL_PERMISSIONS = [
    "view_channels",
    "manage_channels",
    "manage_roles",
    "create_emojis",
    "manage_emojis",
    "view_audit_log",
    "manage_webhooks",
    "manage_server",
    "create_invite",
    "change_nickname",
    "manage_nicknames",
    "kick_members",
    "ban_members",
    "timeout_members",
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
    "embed_links",
    "attach_files",
    "add_reactions",
    "use_external_emojis",
    "use_external_stickers",
    "mention_everyone",
    "mention_here",
    "mention_roles",
    "manage_messages",
    "manage_threads",
    "read_message_history",
    "send_tts_messages",
    "use_app_commands",
    "send_voice_messages",
    "connect",
    "speak",
    "video",
    "use_activities",
    "use_soundboard",
    "use_external_sounds",
    "use_voice_activity",
    "priority_speaker",
    "mute_members",
    "deafen_members",
    "move_members",
    "set_voice_channel_name",
    "create_events",
    "manage_events",
    "administrator"
]

async def manage_role_permissions(ctx: nextcord.Interaction, role_name: str, permissions: str, allow: bool):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.manage_roles:
            await ctx.send("You do not have the required permissions (Manage Roles) to use this command.")
            return
        
        # Get the role object from the role name
        role = nextcord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send("Role not found.")
            return
      
        # Get the author's role and ensure it's not the @everyone role
        author_role = member.top_role
        if author_role == ctx.guild.default_role:
            await ctx.send("You cannot manage permissions from the @everyone role.")
            return
      
        # Prepare the permissions dictionary
        permissions_dict = {}
        for permission in permissions.split(','):
            if hasattr(nextcord.Permissions, permission):
                permissions_dict[permission] = allow
            else:
                await ctx.send(f"Invalid permission '{permission}'.")
                return
      
        try:
            # Update the role permissions
            await role.edit(permissions=nextcord.Permissions(**permissions_dict))
            permission_actions = "allowed" if allow else "revoked"
            permissions_text = ", ".join(permission.replace("_", " ") for permission in permissions.split(','))
            await ctx.send(f"Permissions for {permissions_text} have been {permission_actions} for the role {role.name}.")
        except Exception as e:
            await ctx.send(f"Failed to update role permissions: {e}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="kick", description="Kick a member from the server")
async def kick(ctx: nextcord.Interaction, member: nextcord.Member, reason: str = "No reason provided."):
    # Get the member who invoked the slash command
    author_member = ctx.guild.get_member(ctx.user.id)
    
    # Check if the author has the required permissions to kick members
    if not author_member.guild_permissions.kick_members:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    # Check if the member to be kicked is the bot itself
    if member == ctx.guild.me:
        await ctx.send("You cannot kick the bot.")
        return

    try:
        # Attempt to kick the member
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} has been kicked from the server. Reason: {reason}")
    except nextcord.Forbidden:
        # Handle cases where the bot lacks permissions or the member's role is higher in hierarchy
        await ctx.send("Failed to kick the member. Make sure the bot has the necessary permissions.")
    except Exception as e:
        # Handle other potential errors
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="timeout", description="Timeout a member in the channel")
async def timeout(ctx: nextcord.Interaction, member: nextcord.Member, duration: str, reason: str = "No reason provided."):
    try:
        # Permission Checks
        if not ctx.user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return

        if member == ctx.guild.me:
            await ctx.send("You cannot timeout the bot.")
            return

        # Parse Duration String
        duration_seconds = parse_duration(duration)
        if duration_seconds == -1:
            await ctx.send("Invalid duration format. Please provide a duration between 1 second and 28 days.")
            return

        # Timeout using timeout function (consider visual limitations)
        await member.timeout(timeout=datetime.timedelta(seconds=duration_seconds), reason=reason)

        # Inform the target member and send confirmation message
        try:
            await member.send(f"You have been timed out for {format_duration(duration_seconds)} for the following reason: {reason}")
        except nextcord.Forbidden:
            await ctx.send("Failed to send a DM to the member. They have been timed out, but could not be notified.")
        await ctx.send(f"{member.display_name} has been timed out for {format_duration(duration_seconds)}.")

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

def parse_duration(duration):
    duration_regex = re.compile(r'(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?')
    match = duration_regex.match(duration)
    if match:
        days = int(match.group('days')) if match.group('days') else 0
        hours = int(match.group('hours')) if match.group('hours') else 0
        minutes = int(match.group('minutes')) if match.group('minutes') else 0
        seconds = int(match.group('seconds')) if match.group('seconds') else 0
        total_seconds = (days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60) + seconds
        return min(total_seconds, 28 * 24 * 60 * 60)
    else:
        return -1

def format_duration(duration_seconds):
    periods = [
        ('day', 24 * 60 * 60),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]
    
    parts = []
    for period_name, period_seconds in periods:
        if duration_seconds >= period_seconds:
            num_periods = duration_seconds // period_seconds
            duration_seconds %= period_seconds
            parts.append(f"{num_periods} {period_name}" + ("s" if num_periods > 1 else ""))
    
    if len(parts) == 0:
        return "less than a second"
    else:
        return ", ".join(parts)

@bot.slash_command(name="remove_timeout", description="Remove timeout from a member")
async def remove_timeout(ctx: nextcord.Interaction, member: nextcord.Member):

  # Permission Checks
  if not ctx.user.guild_permissions.administrator:
      await ctx.send("You do not have the required permissions to use this command.")
      return

  if member == ctx.guild.me:
      await ctx.send("You cannot remove timeout from the bot.")
      return

  try:
      # Attempt to remove timeout (using member.timeout with timeout=None)
      await member.timeout(timeout=None, reason="Timeout removed by moderator.")
      await ctx.send(f"The timeout has been removed from {member.display_name}.")

  except nextcord.HTTPException as e:
      # Handle potential errors (e.g., missing permissions, user not timed out)
      if e.code == 403:  # Likely "Forbidden" error (user not timed out)
          await ctx.send(f"{member.display_name} is not currently timed out.")
      else:
          await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="ban", description="Ban a member from the server")
async def ban(ctx: nextcord.Interaction, member: nextcord.Member, reason: str = "No reason provided."):
    # Get the member who invoked the slash command
    author_member = ctx.guild.get_member(ctx.user.id)
    
    # Check if the author has the required permissions to ban members
    if not author_member.guild_permissions.ban_members:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    # Check if the member to be banned is the bot itself
    if member == ctx.guild.me:
        await ctx.send("You cannot ban the bot.")
        return

    try:
        # Attempt to ban the member
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} has been banned from the server. Reason: {reason}")
    except nextcord.Forbidden:
        # Handle cases where the bot lacks permissions or the member's role is higher in hierarchy
        await ctx.send("Failed to ban the member. Make sure the bot has the necessary permissions.")
    except nextcord.HTTPException as e:
        # Handle Discord API-related errors
        await ctx.send(f"Failed to ban the member: {e.text}")
    except Exception as e:
        # Handle other potential errors
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="unban", description="Unban a member from the server")
async def unban(ctx: nextcord.Interaction, member_id: str):
    # Check if the user who invoked the command has the required permissions to unban members
    author_member = ctx.guild.get_member(ctx.user.id)
    if not author_member.guild_permissions.administrator:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    # Attempt to unban the member
    try:
        user = await bot.fetch_user(member_id)
        await ctx.guild.unban(user)
        await ctx.send(f"{user.mention} has been unbanned.")
    except nextcord.NotFound:
        await ctx.send("User not found in the ban list.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="server_info", description="Display information about the server")
async def server_info(ctx: nextcord.Interaction):
    guild = ctx.guild
    embed = nextcord.Embed(title="Server Information", color=nextcord.Color.blue())
    embed.add_field(name="Name", value=guild.name, inline=False)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
    embed.add_field(name="Members", value=guild.member_count, inline=False)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    bucharest_created_at = guild.created_at.astimezone(bucharest_timezone)
    bucharest_created_at_formatted = bucharest_created_at.strftime("%B %d, %Y at %I:%M %p")
    embed.add_field(name="Creation Date", value=bucharest_created_at_formatted, inline=False)
    await ctx.send(embed=embed)

@bot.slash_command(name="server_avatar", description="Display the server's avatar (icon)")
async def server_avatar(ctx: nextcord.Interaction):
    guild = ctx.guild
    # Check if server has an icon and handle potential errors
    if not guild.icon:
        await ctx.send("This server does not have an icon.")
        return

    # Construct and send the embed with the server's icon
    embed = nextcord.Embed(title=f"{guild.name}'s Icon", color=nextcord.Color.blurple())
    embed.set_image(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.slash_command(name="set_server_name", description="Change the server name")
async def set_server_name(ctx: nextcord.Interaction, new_name: str):
    try:
        # Get the member who invoked the command
        member = ctx.guild.get_member(ctx.user.id)
        # Check if the member has administrator permissions
        if not member.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        # Attempt to change the server name
        await ctx.guild.edit(name=new_name)
        await ctx.send(f"Server name has been changed to {new_name}.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to change the server name.")
    except nextcord.HTTPException:
        await ctx.send("An error occurred while changing the server name.")

@bot.slash_command(name="set_server_icon", description="Change the server icon")
async def set_server_icon(ctx: nextcord.Interaction, icon_url: str = None):
    try:
        # Get the member who invoked the command
        member = ctx.guild.get_member(ctx.user.id)

        # Check if the member has administrator permissions
        if not member.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return

        # Handle image input
        if not icon_url and not ctx.message.attachments:
            await ctx.send("Please provide either an image URL or upload an image file.")
            return

        # Fetch the image data
        if icon_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(icon_url) as resp:
                    if resp.status != 200:
                        await ctx.send("Invalid URL or image.")
                        return
                    data = await resp.read()
        else:
            attachment = ctx.message.attachments[0]
            data = await attachment.read()

        # Check the image type
        image_type = imghdr.what(None, data)
        if image_type not in ["jpeg", "png", "gif"]:
            await ctx.send("Unsupported image type. Please provide an image in JPEG, PNG, or GIF format.")
            return

        # Check image size (optional enhancement)
        try:
            image = Image.open(io.BytesIO(data))
            width, height = image.size
            if width < 512 or height < 512:
                await ctx.send("Warning: The image is too small (minimum size is 512x512). Uploading anyway.")
        except OSError:
            # Handle potential errors during image opening (e.g., corrupted image)
            pass

        # Update server icon (Discord enforces minimum resolution)
        await ctx.guild.edit(icon=data)
        await ctx.send("Server icon has been changed.")

    except nextcord.Forbidden:
        await ctx.send("I don't have permission to change the server icon.")
    except nextcord.HTTPException:
        await ctx.send("An error occurred while changing the server icon.")

@bot.slash_command(name="set_server_banner", description="Change the server banner background (requires Server Boosting: Level 2)")
async def set_server_banner(ctx: nextcord.Interaction, banner_url: str):
    member = ctx.guild.get_member(ctx.user.id)
    if not member.guild_permissions.administrator:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    if not ctx.guild.premium_tier >= 2:
        await ctx.send("This command requires Server Boosting (Level 2 or higher) to use.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(banner_url) as resp:
                if resp.status != 200:
                    await ctx.send("Invalid URL or image.")
                    return
                data = await resp.read()

                # Check image type
                image_type = imghdr.what(None, data)
                if image_type not in ["jpeg", "png", "gif"]:
                    await ctx.send("Unsupported image type. Please provide an image in JPEG, PNG, or GIF format.")
                    return

                # Check image dimensions (optional enhancement)
                try:
                    image = Image.open(io.BytesIO(data))
                    width, height = image.size
                    if width < 1920 or height * width < width * (height / 1.777):  # Check for 16:9 aspect ratio
                        await ctx.send("Warning: The image might be too small (minimum size is 1920x1080, 16:9 aspect ratio). Are you sure you want to continue?")
                        confirmation = await ctx.wait_for('message', check=lambda message: message.author == ctx.user)
                        if confirmation.content.lower() not in ['yes', 'y']:
                            await ctx.send("Banner update cancelled.")
                            return
                except OSError:
                    # Handle potential errors during image opening (e.g., corrupted image)
                    pass

                await ctx.guild.edit(banner=data)
                await ctx.send("Server banner background has been changed.")

    except nextcord.Forbidden:
        await ctx.send("I don't have permission to change the server banner background.")
    except nextcord.HTTPException:
        await ctx.send("An error occurred while changing the server banner background.")

@bot.slash_command(name="set_server_splash", description="Change the server splash image (requires Server Boosting: Level 1)")
async def set_server_splash(ctx: nextcord.Interaction, splash_url: str):
    member = ctx.guild.get_member(ctx.user.id)
    if not member.guild_permissions.administrator:
        await ctx.send("You do not have the required permissions to use this command.")
        return
    
    if not ctx.guild.premium_tier >= 1:
        await ctx.send("This command requires Server Boosting (Level 1 or higher) to use.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(splash_url) as resp:
                if resp.status != 200:
                    await ctx.send("Invalid URL or image.")
                    return
                data = await resp.read()

                # Check image type
                image_type = imghdr.what(None, data)
                if image_type not in ["jpeg", "png", "gif"]:
                    await ctx.send("Unsupported image type. Please provide an image in JPEG, PNG, or GIF format.")
                    return

                # Check image dimensions (optional enhancement)
                try:
                    image = Image.open(io.BytesIO(data))
                    width, height = image.size
                    if width < 960 or height * width < width * (height / 1.777):  # Check for 16:9 aspect ratio
                        await ctx.send("Warning: The image might be too small (minimum size is 960x540, 16:9 aspect ratio). Are you sure you want to continue?")
                        confirmation = await ctx.wait_for('message', check=lambda message: message.author == ctx.user)
                        if confirmation.content.lower() not in ['yes', 'y']:
                            await ctx.send("Splash image update cancelled.")
                            return
                except OSError:
                    # Handle potential errors during image opening (e.g., corrupted image)
                    pass

                await ctx.guild.edit(splash=data)
                await ctx.send("Server splash image has been changed.")

    except nextcord.Forbidden:
        await ctx.send("I don't have permission to change the server splash image.")
    except nextcord.HTTPException:
        await ctx.send("An error occurred while changing the server splash image.")

@bot.slash_command(name="mute", description="Mute a member for a set duration")
async def mute(interaction: nextcord.Interaction, member: nextcord.Member, duration: int = 0, unit: str = "minutes", reason: str = "No reason provided."):
    try:
        # Check permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You don't have permission to use this command.")
            return

        # Check duration validity (non-negative)
        if duration < 0:
            await interaction.response.send_message("Invalid duration. Please enter a non-negative number.")
            return

        # Validate unit (minutes, hours, seconds, days)
        valid_units = ("minutes", "hours", "seconds", "days")
        if unit not in valid_units:
            await interaction.response.send_message(f"Invalid unit: {unit}. Please use {', '.join(valid_units)}.")
            return

        # Check for existing "Muted" role
        muted_role = nextcord.utils.get(interaction.guild.roles, name="Muted")

        # If role doesn't exist, create it with specific permissions
        if not muted_role:
            muted_role = await interaction.guild.create_role(name="Muted")

        # Convert duration to seconds based on unit
        conversion_factors = {
            "minutes": 60,
            "hours": 3600,
            "seconds": 1,
            "days": 86400,
        }
        duration_in_seconds = duration * conversion_factors[unit]

        # Handle indefinite mute (duration = 0)
        if duration == 0:
            await member.add_roles(muted_role, reason=reason)
            await interaction.response.send_message(f"{member.mention} has been indefinitely muted.")
            return

        # Warning for durations exceeding Discord's limit
        if duration_in_seconds > 28 * 24 * 60 * 60:
            warning_message = f"**Warning:** Discord's API limits timeouts to a maximum of 28 days. The mute will be enforced for a maximum of 28 days, even if you specify a longer duration."
            await interaction.response.send_message(warning_message)

        # Mute the member with timer
        await member.add_roles(muted_role, reason=reason)
        await interaction.response.send_message(f"{member.mention} has been muted for {duration} {unit}(s).")
        await asyncio.sleep(min(duration_in_seconds, 28 * 24 * 60 * 60))  # Enforce max 28 days

        # Unmute and send success message (check if role still exists)
        if muted_role in interaction.guild.roles and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(f"{member.mention} has been unmuted.")

    except nextcord.HTTPException as e:
        # Handle specific permission errors during role creation (if applicable)
        await interaction.response.send_message(f"An error occurred creating the Muted role: {e}")
    except Exception as e:
        await interaction.response.send_message(f"An unexpected error occurred: {e}")

@bot.slash_command(name="unmute", description="Unmute a member")
async def unmute(interaction: nextcord.Interaction, member: nextcord.Member):
    try:
        # Check if the user invoking the command has the necessary permissions
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You do not have the required permissions to use this command.")
            return
      
        # Find the Muted role
        muted_role = nextcord.utils.get(interaction.guild.roles, name="Muted")
        if not muted_role:
            await interaction.response.send_message("There is no Muted role in this server.")
            return
      
        # Remove the Muted role from the member (if present)
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(f"{member.mention} has been unmuted.")
        else:
            await interaction.response.send_message(f"{member.mention} is not muted.")

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")

@bot.slash_command(name="user_info", description="Get information about a user")
async def user_info(ctx: nextcord.Interaction, member: nextcord.Member):
    embed = nextcord.Embed(title="User Information", color=nextcord.Color.green())

    # Check if user has an avatar, set thumbnail if available
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    embed.add_field(name="Name", value=member.display_name, inline=False)
    bucharest_joined_at = member.joined_at.astimezone(bucharest_timezone)
    bucharest_joined_at_formatted = bucharest_joined_at.strftime("%B %d, %Y at %I:%M %p")
    embed.add_field(name="Joined", value=bucharest_joined_at_formatted, inline=False)
    embed.add_field(name="Roles", value=", ".join([role.name for role in member.roles]), inline=False)
    await ctx.send(embed=embed)

@bot.slash_command(name="user_avatar", description="Display a user's avatar")
async def user_avatar(ctx: nextcord.Interaction, member: nextcord.Member = None):
    # If no user is specified, send an informative message
    if not member:
        await ctx.send("Please specify a user whose avatar you want to see.")
        return

    # Check if user has an avatar and handle potential errors
    if not member.avatar:
        await ctx.send(f"{member.name} does not have an avatar.")
        return

    # Construct and send the embed with the user's avatar
    embed = nextcord.Embed(title=f"{member.name}'s Avatar", color=nextcord.Color.blurple())
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.slash_command(name="list_roles", description="List all roles in the server")
async def list_roles(ctx: nextcord.Interaction):
    roles = ctx.guild.roles
    role_list = "\n".join([role.name for role in roles if role.name != "@everyone"])
    await ctx.send(f"**Roles in this server:**\n{role_list}")

@bot.slash_command(name="assign_role", description="Assign a role to a member")
async def assign_role(ctx: nextcord.Interaction, member: nextcord.Member, role: nextcord.Role):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        await member.add_roles(role)
        await ctx.send(f"Role '{role.name}' has been assigned to {member.display_name}.")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="remove_role", description="Remove a role from a member")
async def remove_role(ctx: nextcord.Interaction, member: nextcord.Member, role: nextcord.Role):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"Role {role.name} has been removed from {member.display_name}.")
        else:
            await ctx.send(f"{member.display_name} does not have the role {role.name}.")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="create_role", description="Create a new role")
async def create_role(ctx: nextcord.Interaction, role_name: str):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        guild = ctx.guild
        existing_role = nextcord.utils.get(guild.roles, name=role_name)
        if existing_role:
            await ctx.send(f"A role with the name {role_name} already exists.")
            return
        else:
            await guild.create_role(name=role_name)
            await ctx.send(f"Role '{role_name}' has been created.")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_role", description="Delete a role")
async def delete_role(ctx: nextcord.Interaction, role_name: str):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        role = nextcord.utils.get(ctx.guild.roles, name=role_name)
        if role:
            await role.delete()
            await ctx.send(f"Role '{role_name}' has been deleted.")
        else:
            await ctx.send(f"No role with the name '{role_name}' found.")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="edit_role", description="Edit a role")
async def edit_role(ctx: nextcord.Interaction, role_name: str, new_name: str = None):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return

        role = nextcord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"No role with the name '{role_name}' found.")
            return

        if new_name:
            await role.edit(name=new_name)

        await ctx.send(f"Role '{role_name}' has been edited.")
    
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="user_roles", description="Display a user's roles")
async def user_roles(ctx: nextcord.Interaction, user: nextcord.Member):
    roles = [role.name for role in user.roles[1:]]  # Exclude @everyone role
    if roles:
        roles_str = ", ".join(roles)
        await ctx.send(f"{user.display_name} has the following roles: {roles_str}")
    else:
        await ctx.send(f"{user.display_name} does not have any roles.")

@bot.slash_command(name="server_stats", description="Get server statistics")
async def server_stats(ctx: nextcord.Interaction):
    total_members = ctx.guild.member_count
    online_members = sum(member.status != nextcord.Status.offline for member in ctx.guild.members)
    text_channels = len(ctx.guild.text_channels)
    voice_channels = len(ctx.guild.voice_channels)
    embed = nextcord.Embed(title="Server Stats", color=nextcord.Color.gold())
    embed.add_field(name="Total Members", value=total_members, inline=False)
    embed.add_field(name="Online Members", value=online_members, inline=False)
    embed.add_field(name="Text Channels", value=text_channels, inline=False)
    embed.add_field(name="Voice Channels", value=voice_channels, inline=False)
    await ctx.send(embed=embed)

@bot.slash_command(name="member_activity", description="Check member activity in the channel")
async def member_activity(ctx: nextcord.Interaction, member: nextcord.Member):
    message_count = len(await ctx.channel.history(limit=None).flatten())
    await ctx.send(f"{member.display_name} has sent {message_count} messages in this channel.")

@bot.slash_command(name="server_activity_stats", description="Display server activity statistics")
async def server_activity_stats(ctx: nextcord.Interaction):
    total_messages = sum(1 for _ in await ctx.channel.history(limit=None).flatten())
    await ctx.send(f"Total messages in this channel: {total_messages}.")

@bot.slash_command(name="most_active_members", description="List most active members")
async def most_active_members(ctx: nextcord.Interaction):
    activity = {}
    async for message in ctx.channel.history(limit=None):
        if message.author not in activity:
            activity[message.author] = 1
        else:
            activity[message.author] += 1
    sorted_members = sorted(activity.items(), key=lambda x: x[1], reverse=True)
    top_members = [f"{member.display_name}: {message_count} messages" for member, message_count in sorted_members[:5]]
    await ctx.send("Top 5 most active members:\n" + "\n".join(top_members))

@bot.slash_command(name="create_emoji", description="Create a custom emoji")
async def create_emoji(ctx: nextcord.Interaction, name: str, url: str):
    try:
        if not ctx.user.guild_permissions.administrator:
            await ctx.send("You don't have permission to manage emojis.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.send(f"Failed to download image from {url}")
                    return

                data = await response.read()

                # Check image size before upload
                if len(data) > 256 * 1024:  # Check for 256 KB limit
                    await ctx.send("Image file size exceeds 256 KB. Please use a smaller image.")
                    return

                # Create the emoji
                try:
                    emoji = await ctx.guild.create_custom_emoji(name=name, image=data)
                    await ctx.send(f"Emoji '{emoji.name}' created: {emoji}")
                except nextcord.HTTPException as e:
                    # Handle specific Discord errors (e.g., invalid image format)
                    if e.code == 10004:  # Unknown Image Format
                        await ctx.send("Invalid image format. Please use a valid image (e.g., PNG, JPG).")
                    else:
                        await ctx.send(f"An error occurred: {e}")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")

@bot.slash_command(name="edit_emoji", description="Edit a custom emoji")
async def edit_emoji(ctx: nextcord.Interaction, current_name: str, new_name: str):
    try:
        if ctx.user.guild_permissions.administrator:
            # Find the emoji by name (assuming it's unique)
            emoji = nextcord.utils.get(ctx.guild.emojis, name=current_name)
            if emoji:
                try:
                    await emoji.edit(name=new_name)
                    await ctx.send(f"Emoji '{current_name}' renamed to '{new_name}'.")
                except nextcord.HTTPException as e:
                    # Handle potential errors (e.g., name already exists)
                    await ctx.send(f"Failed to edit emoji: {e}")
            else:
                await ctx.send("Emoji not found.")
        else:
            await ctx.send("You don't have permission to manage emojis.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_emoji", description="Delete a custom emoji")
async def delete_emoji(ctx: nextcord.Interaction, emoji_name: str):
    try:
        if ctx.user.guild_permissions.administrator:
            # Find the emoji by name (assuming it's unique)
            emoji = nextcord.utils.get(ctx.guild.emojis, name=emoji_name)
            if emoji:
                try:
                    await emoji.delete()
                    await ctx.send(f"Emoji '{emoji_name}' deleted.")
                except nextcord.HTTPException as e:
                    # Handle potential errors (e.g., emoji not found)
                    await ctx.send(f"Failed to delete emoji: {e}")
            else:
                await ctx.send("Emoji not found.")
        else:
            await ctx.send("You don't have permission to manage emojis.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="create_invite", description="Create an invite to a channel")
async def create_invite(ctx: nextcord.Interaction, channel: nextcord.TextChannel, max_uses: int = 1, duration: int = 0):
    try:
        invite = await channel.create_invite(max_uses=max_uses, max_age=duration)
        await ctx.send(f"Invite created: {invite}")
    except Exception as e:
        await ctx.send(f"Failed to create invite: {e}")

@bot.slash_command(name="list_invites", description="List all invites for the server")
async def list_invites(ctx: nextcord.Interaction):
    invites = await ctx.guild.invites()
    if invites:
        invite_list = "\n".join(str(invite) for invite in invites)
        await ctx.send(f"Invites for this server:\n{invite_list}")
    else:
        await ctx.send("No invites found for this server.")

@bot.slash_command(name="verify_user", description="Verify a user")
async def verify_user(ctx: nextcord.Interaction, member: nextcord.Member):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        # Fetch the Verified role
        verified_role = nextcord.utils.get(ctx.guild.roles, name="Verified")
        if not verified_role:
            await ctx.send("Verified role not found.")
            return

        # Add the Verified role to the member
        await member.add_roles(verified_role)
        await ctx.send(f"{member.display_name} has been verified.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="unverify_user", description="Unverify a user")
async def unverify_user(ctx: nextcord.Interaction, member: nextcord.Member):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You do not have the required permissions to use this command.")
            return
        
        # Fetch the Verified role
        verified_role = nextcord.utils.get(ctx.guild.roles, name="Verified")
        if not verified_role:
            await ctx.send("Verified role not found.")
            return

        # Remove the Verified role from the member
        await member.remove_roles(verified_role)
        await ctx.send(f"{member.display_name} has been unverified.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="role_hierarchy", description="View role hierarchy")
async def role_hierarchy(ctx: nextcord.Interaction):
    guild = ctx.guild
    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
    role_list = "\n".join(f"{role.name}: {role.position}" for role in roles)
    await ctx.send(f"Role Hierarchy:\n{role_list}")

@bot.slash_command(name="set_role_position", description="Modify role positions")
async def set_role_position(ctx: nextcord.Interaction, role: nextcord.Role, position: int):
    user = ctx.guild.get_member(ctx.user.id)
    if not user.guild_permissions.administrator:
        await ctx.send("You do not have the required permissions to use this command.")
        return

    # Validate position input
    if not isinstance(position, int) or position < 0 or position >= len(ctx.guild.roles):
        await ctx.send("Invalid position. Please enter a valid integer between 0 and the number of roles in the server.")
        return

    try:
        await role.edit(position=position)
        await ctx.send(f"Role position updated: {role.name} is now at position {position}.")
    except nextcord.errors.HTTPException as e:
        await ctx.send(f"Failed to update role position: {e.code} - {str(e)}")

@bot.slash_command(name="server_boosts", description="Display server boosts")
async def server_boosts(ctx: nextcord.Interaction):
    boosts = ctx.guild.premium_subscription_count
    boosters = [member.mention for member in ctx.guild.premium_subscribers]
    if boosts > 0:
        await ctx.send(f"This server has {boosts} boosts from the following members: {', '.join(boosters)}")
    else:
        await ctx.send("This server has no active boosts.")

@bot.slash_command(name="coin", description="Flip a coin")
async def coin(ctx: nextcord.Interaction):
    # Generate a random number (0 or 1) to represent heads or tails
    result = random.choice(["Heads", "Tails"])
    
    await ctx.send(f"The coin landed on: {result} 🪙")

@bot.slash_command(name="roll", description="Roll a dice")
async def roll(ctx: nextcord.Interaction, dice: str):
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception as e:
        await ctx.send('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.send(result)

@bot.slash_command(name="slowmode", description="Set slow mode in the channel")
async def slowmode(ctx: nextcord.Interaction, duration: int):
    user = ctx.guild.get_member(ctx.user.id)
    if not user.guild_permissions.administrator:
        await ctx.send("You don't have permission to manage channels.")
        return
    
    if duration < 0 or duration > 21600:  
        await ctx.send("Invalid duration. Please provide a value between 0 and 21600 seconds.")
        return
        
    try:
        await ctx.channel.edit(slowmode_delay=duration)
        await ctx.send(f"Slow mode has been set to {duration} seconds in this channel.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to manage channels.")

@bot.slash_command(name="remove_slowmode", description="Remove slow mode from the channel")
async def remove_slowmode(ctx: nextcord.Interaction):
    user = ctx.guild.get_member(ctx.user.id)
    if not user.guild_permissions.administrator:
        await ctx.send("You don't have permission to manage channels.")
        return
    
    try:
        await ctx.channel.edit(slowmode_delay=0)
        await ctx.send("Slow mode has been removed from this channel.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to manage channels.")

@bot.slash_command(name="create_voice_channel", description="Create a voice channel")
async def create_voice_channel(ctx: nextcord.Interaction, category_name: str, channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.manage_channels:
            await ctx.send("You don't have permission to create voice channels.")
            return

        guild = ctx.guild
        category = nextcord.utils.get(guild.categories, name=category_name)
        
        if category:
            existing_channel = nextcord.utils.get(category.voice_channels, name=channel_name)
            if existing_channel:
                await ctx.send(f"A voice channel with the name '{channel_name}' already exists in the category '{category_name}'.")
                return
            
            await guild.create_voice_channel(channel_name, category=category)
            await ctx.send(f"Voice channel '{channel_name}' has been created under category '{category_name}'.")
        else:
            await ctx.send(f"No category with the name '{category_name}' found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="delete_voice_channel", description="Delete a voice channel")
async def delete_voice_channel(ctx: nextcord.Interaction, category_name: str, channel_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.manage_channels:
            await ctx.send("You don't have permission to delete voice channels.")
            return

        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        
        if category:
            channel = nextcord.utils.get(category.voice_channels, name=channel_name)
            if channel:
                await channel.delete()
                await ctx.send(f"Voice channel {channel_name} has been deleted from the category {category_name}.")
            else:
                await ctx.send(f"No voice channel with the name {channel_name} found in the category {category_name}.")
        else:
            await ctx.send(f"No category with the name {category_name} found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="rename_voice_channel", description="Rename a voice channel")
async def rename_voice_channel(ctx: nextcord.Interaction, category_name: str, old_name: str, new_name: str):
    try:
        member = ctx.guild.get_member(ctx.user.id)
        if not member.guild_permissions.manage_channels:
            await ctx.send("You don't have permission to rename voice channels.")
            return
        
        category = nextcord.utils.get(ctx.guild.categories, name=category_name)
        if category:
            existing_channel = nextcord.utils.get(category.voice_channels, name=new_name)
            if existing_channel:
                await ctx.send(f"A voice channel with the name '{new_name}' already exists in the category '{category_name}'.")
                return
            
            channel = nextcord.utils.get(category.voice_channels, name=old_name)
            if channel:
                await channel.edit(name=new_name)
                await ctx.send(f"Voice channel name has been changed from '{old_name}' to '{new_name}' in the category '{category_name}'.")
            else:
                await ctx.send(f"No voice channel with the name '{old_name}' found in the category '{category_name}'.")
        else:
            await ctx.send(f"No category with the name '{category_name}' found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="set_nickname", description="Set a nickname for a member")
async def set_nickname(ctx: nextcord.Interaction, member: nextcord.Member, nickname: str):
    if member == ctx.guild.me or member == ctx.user:
        await ctx.send("Sorry, you cannot change your own nickname or the bot's nickname.")
        return
    
    if ctx.user.guild_permissions.manage_nicknames:
        try:
            old_nickname = member.display_name
            await member.edit(nick=nickname)
            await ctx.send(f"Nickname was changed from {old_nickname} to {nickname} for {member.display_name}.")
        except nextcord.Forbidden:
            await ctx.send("I don't have permission to change the nickname.")
    else:
        await ctx.send("You don't have permission to manage nicknames.")

@bot.slash_command(name="reset_nickname", description="Reset a member's nickname")
async def reset_nickname(ctx: nextcord.Interaction, member: nextcord.Member):
    if ctx.user.guild_permissions.manage_nicknames:
        try:
            await member.edit(nick=None)
            await ctx.send(f"Nickname reset for {member.display_name}.")
        except nextcord.Forbidden:
            await ctx.send("I don't have permission to change the nickname.")
    else:
        await ctx.send("You don't have permission to manage nicknames.")

@bot.slash_command(name="announce", description="Send an announcement message")
async def announce(ctx: nextcord.Interaction, message: str):
    try:
        if not ctx.user.guild_permissions.administrator:
            await ctx.send("You don't have permission to manage channels.")
            return
        
        announcement_channel = nextcord.utils.get(ctx.guild.channels, name="announcements")
        if announcement_channel:
            await announcement_channel.send(message)
        else:
            await ctx.send("Announcement channel not found. Please create one.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="set_rules", description="Set rules in an embed format")
async def set_rules(ctx: nextcord.Interaction, *, rules: str):
    try:
        # Check if the user has administrator permissions
        if not ctx.user.guild_permissions.administrator:
            await ctx.send("You do not have permission to set the rules.")
            return
        
        # Get the rules channel
        rules_channel = nextcord.utils.get(ctx.guild.channels, name="rules")
        if rules_channel:
            # Split the provided rules string into individual rules
            rules_list = rules.split(";")
            
            # Construct the embed with the rules as a numbered list
            embed_description = "\n".join([f"{index}. {rule.strip()}" for index, rule in enumerate(rules_list, start=1)])
            embed_description += "\nPlease read and abide by the rules."
            embed = nextcord.Embed(title="Server Rules", description=embed_description, color=nextcord.Color.blue())
            
            # Send the embed to the rules channel
            await rules_channel.send(embed=embed)
            await ctx.send("Rules have been successfully updated.")
        else:
            await ctx.send("Rules channel not found. Please create one.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="user_activity", description="View user activity")
async def user_activity(ctx: nextcord.Interaction, member: nextcord.Member):
    embed = nextcord.Embed(title=f"User Activity - {member.display_name}", color=nextcord.Color.blue())
    embed.add_field(name="Last Seen Online", value=member.status, inline=False)
    # Add more fields for message count, join date, etc.
    await ctx.send(embed=embed)

@bot.slash_command(name="pin", description="Pin a message by its ID")
async def pin(ctx: nextcord.Interaction, message_id: str):
    # Check if the bot has the necessary permissions
    if not ctx.guild.me.guild_permissions.manage_messages:
        await ctx.send("I don't have permission to manage messages.")
        return

    # Attempt to fetch the message
    try:
        message = await ctx.channel.fetch_message(int(message_id))
        await message.pin()
        await ctx.send(f"Message with ID {message_id} has been pinned.")
    except nextcord.NotFound:
        await ctx.send("Message not found. Please ensure you provided a valid message ID.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to pin messages.")
    except nextcord.HTTPException:
        await ctx.send("Failed to pin the message. Please try again later.")

@bot.slash_command(name="unpin", description="Unpin a message by its ID")
async def unpin(ctx: nextcord.Interaction, message_id: str):
    # Check if the bot has the necessary permissions
    if not ctx.guild.me.guild_permissions.manage_messages:
        await ctx.send("I don't have permission to manage messages.")
        return

    # Attempt to fetch the message
    try:
        message = await ctx.channel.fetch_message(int(message_id))
        await message.unpin()
        await ctx.send(f"Message with ID {message_id} has been unpinned.")
    except nextcord.NotFound:
        await ctx.send("Message not found. Please ensure you provided a valid message ID.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to unpin messages.")
    except nextcord.HTTPException:
        await ctx.send("Failed to unpin the message. Please try again later.")

@bot.slash_command(name="mention_everyone", description="Mention @everyone (Admin Only)")
async def mention_everyone(ctx: nextcord.Interaction):
    try:
        if ctx.user.guild_permissions.administrator:
            await ctx.send("@everyone")
        else:
            await ctx.send("You don't have permission to use this command.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.slash_command(name="set_prefix", description="Set prefix to a new symbol")
async def set_prefix(ctx, prefix):
    if not ctx.user.guild_permissions.administrator:
        await ctx.send("Only administrators can use this command.")
        return

    bot.command_prefix = prefix
    await ctx.send(f"Prefix set to: {prefix}")

@bot.slash_command(name="reset_prefix", description="Reset prefix to default symbol")
async def reset_prefix(ctx):
    if not ctx.user.guild_permissions.administrator:
        await ctx.send("Only administrators can use this command.")
        return

    bot.command_prefix = "!"
    prefix = bot.command_prefix
    await ctx.send(f"Prefix reset to default: {prefix}")

@bot.slash_command(name="rename_thread", description="Rename the specified thread (requires Manage Threads permission)")
async def rename_thread(ctx: nextcord.Interaction, thread_id: str, new_title: str):
    try:
        # Ensure the user has permission to manage threads
        if not ctx.user.guild_permissions.manage_threads:
            await ctx.send("You don't have this permission.")
            return
        
        # Attempt to convert the thread ID to an integer
        try:
            thread_id = int(thread_id)
        except ValueError:
            await ctx.send("Invalid thread ID. Please provide a valid thread ID.")
            return
        
        # Fetch the thread by its ID
        thread = await bot.fetch_channel(thread_id)
        if not isinstance(thread, nextcord.Thread):
            await ctx.send("Thread not found or provided ID is not a thread.")
            return
        
        # Rename the thread
        await thread.edit(name=new_title)
        await ctx.send(f"Thread renamed to: {new_title}")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to rename threads in this channel.")
    except nextcord.HTTPException as e:
        await ctx.send(f"Error renaming thread: {e}")
    except Exception as ex:
        await ctx.send(f"An error occurred: {ex}")

@bot.slash_command(name="delete_thread", description="Delete the specified thread (requires Manage Threads permission)")
async def delete_thread(ctx: nextcord.Interaction, thread_id: str):
    try:
        # Ensure the user has permission to manage threads
        if not ctx.user.guild_permissions.manage_threads:
            await ctx.send("You don't have permission to manage threads.")
            return
        
        # Attempt to convert the thread ID to an integer
        try:
            thread_id = int(thread_id)
        except ValueError:
            await ctx.send("Invalid thread ID. Please provide a valid thread ID.")
            return
        
        # Fetch the thread by its ID
        thread = await bot.fetch_channel(thread_id)
        if not isinstance(thread, nextcord.Thread):
            await ctx.send("Thread not found or provided ID is not a thread.")
            return
        
        # Delete the thread
        await thread.delete()
        await ctx.send("Thread deleted successfully.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to delete threads in this channel.")
    except nextcord.HTTPException as e:
        await ctx.send(f"Error deleting thread: {e}")
    except Exception as ex:
        await ctx.send(f"An error occurred: {ex}")

@bot.slash_command(name="open_thread", description="Open the specified closed thread (requires Manage Threads permission)")
async def open_thread(ctx: nextcord.Interaction, thread_id: str):
    try:
        # Ensure the user has permission to manage threads
        if not ctx.user.guild_permissions.manage_threads:
            await ctx.send("You don't have permission to manage threads.")
            return
        
        # Attempt to convert the thread ID to an integer
        try:
            thread_id = int(thread_id)
        except ValueError:
            await ctx.send("Invalid thread ID. Please provide a valid thread ID.")
            return
        
        # Fetch the thread by its ID
        thread = await bot.fetch_channel(thread_id)
        if not isinstance(thread, nextcord.Thread):
            await ctx.send("Thread not found or provided ID is not a thread.")
            return
        
        # Check if the thread is closed
        if not thread.archived:
            await ctx.send("Thread is already open.")
            return
        
        # Open the thread
        await thread.edit(archived=False)
        await ctx.send("Thread opened successfully.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to open threads in this channel.")
    except nextcord.HTTPException as e:
        await ctx.send(f"Error opening thread: {e}")
    except Exception as ex:
        await ctx.send(f"An error occurred: {ex}")

@bot.slash_command(name="close_thread", description="Close the specified open thread (requires Manage Threads permission)")
async def close_thread(ctx: nextcord.Interaction, thread_id: str):
    try:
        # Ensure the user has permission to manage threads
        if not ctx.user.guild_permissions.manage_threads:
            await ctx.send("You don't have permission to manage threads.")
            return
        
        # Attempt to convert the thread ID to an integer
        try:
            thread_id = int(thread_id)
        except ValueError:
            await ctx.send("Invalid thread ID. Please provide a valid thread ID.")
            return
        
        # Fetch the thread by its ID
        thread = await bot.fetch_channel(thread_id)
        if not isinstance(thread, nextcord.Thread):
            await ctx.send("Thread not found or provided ID is not a thread.")
            return
        
        # Check if the thread is already closed
        if thread.archived:
            await ctx.send("Thread is already closed.")
            return
        
        # Close the thread
        await thread.edit(archived=True)
        await ctx.send("Thread closed successfully.")
    except nextcord.Forbidden:
        await ctx.send("I don't have permission to close threads in this channel.")
    except nextcord.HTTPException as e:
        await ctx.send(f"Error closing thread: {e}")
    except Exception as ex:
        await ctx.send(f"An error occurred: {ex}")

@bot.slash_command(name="embed_link", description="Send an embedded link message")
async def embed_link(ctx: nextcord.Interaction):
    await ctx.send("Check out this embedded link: https://www.youtube.com/watch?v=dQw4w9WgXcQ")

@bot.slash_command(name="embed_with_link", description="Send an embedded message with a link")
async def embed_with_link(ctx: nextcord.Interaction):
    embed = nextcord.Embed(title="Check out this embedded link!", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", color=nextcord.Color.blue())
    await ctx.send(embed=embed)

@bot.slash_command(name="weather", description="Get weather information for a location")
async def weather(ctx: nextcord.Interaction, location: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data["cod"] == 200:
                weather_description = data["weather"][0]["description"]
                temperature_celsius = int(data["main"]["temp"])  # Convert to integer
                temperature_fahrenheit = int(temperature_celsius * 9/5 + 32)  # Convert to integer
                humidity = data["main"]["humidity"]
                wind_speed_kmh = int(data["wind"]["speed"] * 3.6)  # Convert to integer
                wind_speed_mph = int(data["wind"]["speed"] * 2.237)  # Convert to integer
                icon_code = data["weather"][0]["icon"]
                icon_url = f"http://openweathermap.org/img/wn/{icon_code}.png"

                embed = nextcord.Embed(title=f"Weather in {location}", color=0x7289DA)
                embed.set_thumbnail(url=icon_url)
                embed.add_field(name="Description", value=weather_description, inline=False)
                embed.add_field(name="Temperature", value=f"{temperature_celsius}°C ({temperature_fahrenheit}°F)", inline=True)
                embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                embed.add_field(name="Wind Speed", value=f"{wind_speed_kmh} km/h ({wind_speed_mph} mph)", inline=True)

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Could not find weather data for {location}")

@bot.slash_command(name="exit", description="Shut down the bot")
async def exit(ctx: nextcord.Interaction):
    try:
        user = ctx.guild.get_member(ctx.user.id)
        if not user.guild_permissions.administrator:
            await ctx.send("You don't have permission to shut down the bot.")
            return
        
        await ctx.send("Shutting down...")
        await bot.close()
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")