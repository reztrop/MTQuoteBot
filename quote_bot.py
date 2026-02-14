import os
import discord
from discord.ext import commands

# Configuration
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # We'll set this in the terminal
QUOTES_CHANNEL_ID = 1440372391845953606  # <-- replace this with your quotes channel ID
QUOTE_EMOJI = "🟢"
MIN_REACTIONS = 3

# Intents tell Discord what events we care about
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Track quoted messages: {original_message_id: (channel_id, quote_embed_message_id)}
quoted_messages = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

async def update_quote_reaction_count(original_msg_id, quotes_channel):
    """Update the reaction count on an existing quote embed"""
    try:
        # Get the channel ID and quote message ID from our tracking dict
        tracked_info = quoted_messages.get(original_msg_id)
        if not tracked_info:
            return

        original_channel_id, quote_msg_id = tracked_info

        # Fetch the original message to get updated reaction count
        original_channel = bot.get_channel(original_channel_id)
        if not original_channel:
            original_channel = await bot.fetch_channel(original_channel_id)

        original_message = await original_channel.fetch_message(original_msg_id)

        # Find the green circle reaction count
        quote_reaction = None
        for reaction in original_message.reactions:
            if str(reaction.emoji) == QUOTE_EMOJI:
                quote_reaction = reaction
                break

        if not quote_reaction:
            return

        # Fetch the quote embed message and update it
        quote_msg = await quotes_channel.fetch_message(quote_msg_id)

        if quote_msg.embeds:
            # Update the existing embed
            embed = quote_msg.embeds[0]
            embed.set_footer(text=f"🟢 {quote_reaction.count} reactions")
            await quote_msg.edit(embed=embed)

    except discord.NotFound:
        # Quote message was deleted, remove from tracking so it can be re-posted
        if original_msg_id in quoted_messages:
            del quoted_messages[original_msg_id]
            print(f"Quote message was deleted, removed tracking for message {original_msg_id}")
    except Exception as e:
        print(f"Error updating quote reaction count: {e}")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore reactions from the bot itself
    if payload.user_id == bot.user.id:
        return

    # Check if already quoted - if so, update the reaction count
    if payload.message_id in quoted_messages:
        # Get quotes channel first
        quotes_channel = bot.get_channel(QUOTES_CHANNEL_ID)
        if quotes_channel is None:
            try:
                quotes_channel = await bot.fetch_channel(QUOTES_CHANNEL_ID)
            except Exception:
                return
        # Update existing quote embed with new reaction count
        await update_quote_reaction_count(payload.message_id, quotes_channel)

        # If update removed the tracking (quote was deleted), continue to re-post
        # Otherwise, we're done updating
        if payload.message_id in quoted_messages:
            return

    # Only care about the green circle emoji
    if str(payload.emoji) != QUOTE_EMOJI:
        return

    # Get the channel and message that was reacted to
    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        channel = await bot.fetch_channel(payload.channel_id)

    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        # Can't get the message for some reason; just stop
        return

    # Find the green-circle reaction and count how many there are
    quote_reaction = None
    for reaction in message.reactions:
        if str(reaction.emoji) == QUOTE_EMOJI:
            quote_reaction = reaction
            break

    # If there are not enough reactions yet, do nothing
    if quote_reaction is None or quote_reaction.count < MIN_REACTIONS:
        return

    # Get the quotes channel
    quotes_channel = bot.get_channel(QUOTES_CHANNEL_ID)
    if quotes_channel is None:
        try:
            quotes_channel = await bot.fetch_channel(QUOTES_CHANNEL_ID)
        except Exception:
            return

    author = message.author.display_name
    jump_link = message.jump_url

    # Check if this is a voice message
    is_voice = message.flags.is_voice_message if hasattr(message.flags, 'is_voice_message') else False

    # Build the content of the quote
    if not message.content and not message.attachments:
        content_text = "*[Message had no text]*"
    else:
        content_text = message.content if message.content else ""

    # Add voice message indicator
    if is_voice:
        if content_text:
            content_text = "🎙️ **Voice Message**\n" + content_text
        else:
            content_text = "🎙️ **Voice Message**"

    # If there are attachments (images, etc.), include their URLs underneath
    if message.attachments:
        attachment_texts = [att.url for att in message.attachments]
        if content_text:
            content_text += "\n"
        content_text += "\n".join(attachment_texts)

    # Format the quote content (jump link now in author name)
    formatted_content = content_text

    # Create embed for the quote
    embed = discord.Embed(
        description=formatted_content,
        color=discord.Color.green()
    )

    # Add author with profile picture and clickable name
    embed.set_author(
        name=author,
        icon_url=message.author.display_avatar.url,
        url=jump_link
    )

    # Add footer with reaction count only
    embed.set_footer(text=f"🟢 {quote_reaction.count} reactions")

    # Send the embed and store the quote message ID
    quote_msg = await quotes_channel.send(embed=embed)

    # Mark as quoted and store both channel ID and quote message ID for future updates
    quoted_messages[message.id] = (channel.id, quote_msg.id)

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable not set.")
    bot.run(TOKEN)
