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

# Track quoted messages to prevent duplicates
quoted_messages = set()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore reactions from the bot itself
    if payload.user_id == bot.user.id:
        return

    # Check if already quoted
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

    # Format as a block quote in Discord
    quoted_lines = content_text.replace("\n", "\n> ")
    quote_text = (
        f"> {quoted_lines}\n"
        f"— **{author}** in {channel.mention}"
    )

    await quotes_channel.send(quote_text)

    # Mark as quoted to prevent duplicates
    quoted_messages.add(message.id)

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable not set.")
    bot.run(TOKEN)
