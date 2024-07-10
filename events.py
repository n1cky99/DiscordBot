import nextcord
from bot_setup import bot, bucharest_timezone
import datetime

@bot.event
async def on_ready():
    print("Hello! The bot is up and ready to go!")
    for guild in bot.guilds:
        general_channel = nextcord.utils.get(guild.text_channels, name="general")
        if general_channel:
            await general_channel.send("Hello! The bot is up and ready to go!")
            break 

@bot.event
async def on_message_edit(before, after):
    if before.content != after.content:
        log_channel = nextcord.utils.get(after.guild.channels, name="message-logs")  # Adjust channel name accordingly
        
        embed = nextcord.Embed(description=f"Message edited in {after.channel.mention} - [Jump to message](https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id})", color=nextcord.Color.yellow())
        embed.set_author(name=after.author.display_name, icon_url=after.author.avatar.url if after.author.avatar else after.author.default_avatar.url)
        embed.add_field(name="Old", value=before.content, inline=False)
        embed.add_field(name="New", value=after.content, inline=False)
        bucharest_edited_at = after.edited_at.astimezone(bucharest_timezone)
        bucharest_edited_at_formatted = bucharest_edited_at.strftime("%B %d, %Y at %I:%M %p")
        embed.set_footer(text=f"User ID: {after.author.id} • {bucharest_edited_at_formatted}")

        await log_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    log_channel = nextcord.utils.get(message.guild.channels, name="message-logs")  # Adjust channel name accordingly
    if log_channel:
        try:
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

@bot.event
async def on_member_join(member):
    welcome_channel = nextcord.utils.get(member.guild.channels, name="welcome")
    if welcome_channel:
        try:
            default_avatar_url = member.default_avatar.url
            embed = nextcord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=f"Welcome {member.mention} to {member.guild.name}! Enjoy your stay.",
                color=nextcord.Color.green()
            )
            embed.set_thumbnail(url=default_avatar_url)
            await welcome_channel.send(embed=embed)
        except nextcord.Forbidden:
            print(f"Error: Bot does not have permissions to send messages in {welcome_channel.name}")
        except Exception as e:
            print(f"Error sending welcome message: {e}")

@bot.event
async def on_member_remove(member):
    goodbye_channel = nextcord.utils.get(member.guild.channels, name="welcome")
    if goodbye_channel:
        try:
            default_avatar_url = member.default_avatar.url
            embed = nextcord.Embed(
                title="Goodbye!",
                description=f"Goodbye {member.display_name}! We'll miss you.",
                color=nextcord.Color.red()
            )
            embed.set_thumbnail(url=default_avatar_url)
            await goodbye_channel.send(embed=embed)
        except nextcord.Forbidden:
            print(f"Error: Bot does not have permissions to send messages in {goodbye_channel.name}")
        except Exception as e:
            print(f"Error sending goodbye message: {e}")

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        log_channel = nextcord.utils.get(after.guild.channels, name="message-logs")  # Adjust channel name accordingly
        if log_channel:
            await log_channel.send(f"{after.display_name}'s nickname changed from {before.nick} to {after.nick}.")

# Event to log role changes
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added_roles = [role.name for role in after.roles if role not in before.roles]
        removed_roles = [role.name for role in before.roles if role not in after.roles]
        log_channel = nextcord.utils.get(after.guild.channels, name="role-logs")  # Adjust channel name accordingly
        if log_channel:
            if added_roles:
                await log_channel.send(f"{after.display_name} was assigned the following roles: {', '.join(added_roles)}.")
            if removed_roles:
                await log_channel.send(f"{after.display_name} was removed from the following roles: {', '.join(removed_roles)}.")

# Event to log role hierarchy changes
@bot.event
async def on_guild_role_update(before, after):
    if before.position != after.position:
        log_channel = nextcord.utils.get(after.guild.channels, name="role-logs")
        if log_channel:
            await log_channel.send(f"Role position updated: {before.name} moved from position {before.position} to {after.position}.")

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        log_channel = nextcord.utils.get(member.guild.channels, name="voice-channel-logs")  # Adjust channel name accordingly
        
        if before.channel:
            action = "left"
            channel = before.channel
            color = nextcord.Color.red()  # Red color for leaving voice channel
        elif after.channel:
            action = "joined"
            channel = after.channel
            color = nextcord.Color.green()  # Green color for joining voice channel
        
        if log_channel:
            embed = nextcord.Embed(description=f"{member.mention} has {action} {channel.mention} voice channel.", color=color)
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            await log_channel.send(embed=embed)

user_message_counts = {}

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the message is in the spam channel
    if message.channel.name == "spam":
        return

    # Check if the user has admin permissions
    user = message.guild.get_member(message.author.id)
    if user and user.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    # Update message count for the user
    user_id = message.author.id
    if user_id not in user_message_counts:
        user_message_counts[user_id] = {"count": 1, "last_message": message.content}
    else:
        user_message_counts[user_id]["count"] += 1
        if user_message_counts[user_id]["last_message"] == message.content:
            if user_message_counts[user_id]["count"] >= 5:
                # Warn the user
                await message.channel.send(f"{message.author.mention}, please don't spam the same message! "
                                           f"Your duplicate messages have been deleted.")
                # Delete the repeated messages in the current channel
                async for msg in message.channel.history(limit=200):
                    if msg.author == message.author and msg.content == message.content:
                        await msg.delete()
                        user_message_counts[user_id]["count"] -= 1  # Decrement count for deleted message
                        if user_message_counts[user_id]["count"] <= 1:  # Ensure only one message remains
                            break
        else:
            user_message_counts[user_id]["last_message"] = message.content

    await bot.process_commands(message)

@bot.event
async def on_message(message):
    # Ignore messages from your bot
    if message.author == bot.user:
        return

    # Check for admin permissions
    is_admin = message.author.guild_permissions.administrator

    # Filter only for non-admins
    if not is_admin:
        # Define bad words (list format for easy modification)
        bad_words = ["badword1", "badword2"]

        # Check for bad words (case-insensitive)
        if any(word.lower() in message.content.lower() for word in bad_words):
            await message.delete()
            await message.channel.send(f"Hey {message.author.mention}, these contents are not allowed.")

        # Define disallowed link prefixes (list format for easy modification)
        link_prefixes = ["example1.com", "example2.com"]

        # Check for links
        if any(link in message.content for link in link_prefixes):
            await message.delete()
            await message.channel.send(f"Hey {message.author.mention}, these links are not allowed here.")

        # Define additional bad words (list format for easy modification)
        bad_words2 = ["badword3", "badword4"]

        # Check for bad words and apply timeout
        if any(word.lower() in message.content.lower() for word in bad_words2):
            timeout_duration = datetime.timedelta(seconds=60)  # Adjust as needed
            await message.delete()
            await message.author.timeout(timeout_duration, reason="Using forbidden language")
            await message.channel.send(f"Hey {message.author.mention}, that language is not allowed. You are timed out for {timeout_duration.seconds} seconds.")

        # Define additional disallowed link prefixes (list format for easy modification)
        link_prefixes2 = ["example3.com", "example4.com"]

        # Check for links and apply timeout
        if any(link in message.content for link in link_prefixes2):
            timeout_duration = datetime.timedelta(seconds=60)  # Adjust as needed
            await message.delete()
            await message.author.timeout(timeout_duration, reason="Posting disallowed links")
            await message.channel.send(f"Hey {message.author.mention}, these links are not allowed here. You are timed out for {timeout_duration.seconds} seconds.")
        
        # Define banned phrases (list format for easy modification)
        banned_phrases = ["ban @everyone", "ban everyone"]  # Adjust as needed

        # Check for banned phrases, excluding mentions and embeds
        if any(phrase in message.content.lower() for phrase in banned_phrases) and not message.mentions and not message.embeds:
            await message.channel.send(f"**WARNING:** {message.author.mention}, attempting to usurp admin privileges or manipulate the ban system is a serious offense. You have been banned.")
            await message.author.ban(reason="Attempting unauthorized ban or manipulation")
            await message.delete()

@bot.event
async def on_guild_update(before: nextcord.Guild, after: nextcord.Guild):
    # Log major server changes (name, icon)
    log_channel = nextcord.utils.get(after.text_channels, name="message-logs")  # Adjust channel name

    if log_channel:
        if before.name != after.name:
            embed = nextcord.Embed(
                title="Server Name Changed",
                description=f"Server name changed from **{before.name}** to **{after.name}**.",
                color=nextcord.Color.orange()
            )
            await log_channel.send(embed=embed)

        if before.icon != after.icon:
            embed = nextcord.Embed(
                title="Server Icon Changed",
                description=f"Server icon has been changed.",
                color=nextcord.Color.orange()
            )
            embed.set_image(url=after.icon.url)  # Include the new icon image
            await log_channel.send(embed=embed)