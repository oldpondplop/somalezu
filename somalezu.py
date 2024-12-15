import asyncio
import logging
import os
from functools import wraps

import discord
# import youtube_dl
from pathlib import Path

import yt_dlp as youtube_dl
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
from dotenv import load_dotenv

discord.utils.setup_logging(
    # handler=logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w'),
    level=logging.DEBUG,
    root=True,
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
MY_GUILD = discord.Object(id=int(GUILD_ID))

if TOKEN is None:
    raise ValueError("No DISCORD_TOKEN found")

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

# ffmpeg options
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

SOUNDBOARD_MAPPING = {
    '🎵': 'sounds/cena.mp3',
    '🎸': 'sounds/obamna.mp3',
    '🎹': 'sounds/cookie.mp3',
    '🥁': 'sounds/cop.mp3',
    '🎻': 'sounds/fake.mp3'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        

def ensure_voice_connection(func):
    """Decorator to ensure the bot is connected to the user's voice channel before executing the command."""
    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
            return
        if interaction.guild.voice_client is None:
            await interaction.user.voice.channel.connect()
        return await func(self, interaction, *args, **kwargs)
    return wrapper

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.soundboard_mapping = SOUNDBOARD_MAPPING  # Soundboard emoji-to-file mapping
        self.current_youtube_source = {}  # To store the current YouTube audio source per guild
        self.was_youtube_playing = {}  # To track if YouTube audio was playing before soundboard

    @discord.app_commands.command(name="play", description="Plays from a URL")
    @discord.app_commands.describe(url="The URL to play from")
    @ensure_voice_connection
    async def play(self, interaction: discord.Interaction, url: str):
        """Streams audio from a URL"""
        await interaction.response.defer(ephemeral=True)
        try:
            # Create a YouTube audio source
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
            
            # Start playback and store the YouTube source
            voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            self.current_youtube_source[interaction.guild.id] = player  # Store the YouTube source
            await interaction.followup.send(f'Now streaming: {player.title}', ephemeral=True)
        except Exception as e:
            logger.exception('Error in stream command: %s', str(e))
            await interaction.followup.send("Failed to stream the requested URL.", ephemeral=True)

    @discord.app_commands.command(name="resume", description="Resumes paused audio playback")
    @ensure_voice_connection
    async def resume(self, interaction: discord.Interaction):
        """Resumes the currently paused YouTube audio"""
        voice_client = interaction.guild.voice_client
        guild_id = interaction.guild.id
        if voice_client and voice_client.is_paused():
            if guild_id in self.current_youtube_source:  # Only resume if it's YouTube audio
                voice_client.resume()
                await interaction.response.send_message("Playback resumed.", ephemeral=True)
            else:
                await interaction.response.send_message("Cannot resume non-YouTube playback.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio is currently paused.", ephemeral=True)

    @discord.app_commands.command(name="pause", description="Pauses the current audio playback")
    @ensure_voice_connection
    async def pause(self, interaction: discord.Interaction):
        """Pauses the currently playing YouTube audio"""
        voice_client = interaction.guild.voice_client
        guild_id = interaction.guild.id
        if voice_client and voice_client.is_playing() and guild_id in self.current_youtube_source:
            voice_client.pause()
            await interaction.response.send_message("Playback paused.", ephemeral=True)
        else:
            await interaction.response.send_message("No YouTube audio is currently playing.", ephemeral=True)

    @discord.app_commands.command(name="soundboard", description="Select and play a sound from the soundboard")
    @ensure_voice_connection
    async def soundboard(self, interaction: discord.Interaction):
        """Displays a soundboard with buttons for each sound."""
        view = self.SoundboardView(interaction.guild.voice_client, self)
        await interaction.response.send_message("Choose a sound to play:", view=view, ephemeral=True)

    class SoundboardView(View):
        def __init__(self, voice_client, music_cog):
            super().__init__(timeout=60)
            self.voice_client = voice_client
            self.music_cog = music_cog

            for emoji, file_path in music_cog.soundboard_mapping.items():
                button = Button(emoji=emoji, style=discord.ButtonStyle.primary)
                button.callback = self.make_sound_callback(file_path)
                self.add_item(button)

        def make_sound_callback(self, file_path):
            async def play_sound(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True)

                # Save the current YouTube audio state
                guild_id = interaction.guild.id
                if self.voice_client.is_playing() and guild_id in self.music_cog.current_youtube_source:
                    self.music_cog.was_youtube_playing[guild_id] = True
                    self.voice_client.pause()  # Pause current YouTube playback
                else:
                    self.music_cog.was_youtube_playing[guild_id] = False

                # Play the soundboard audio
                def after_playback(e):
                    if e:
                        logger.error(f"Soundboard playback error: {e}")
                    # Resume YouTube playback if it was playing
                    if self.music_cog.was_youtube_playing.get(guild_id, False):
                        self.voice_client.play(self.music_cog.current_youtube_source[guild_id], after=None)

                self.voice_client.play(
                    discord.FFmpegPCMAudio(file_path),
                    after=after_playback
                )

            return play_sound

class Somalezu(commands.Bot):
    def __init__(self, *, command_prefix, description, intents):
        super().__init__(command_prefix=command_prefix, intents=intents, description=description)

    async def setup_hook(self):
        # Add only the Music cog since it now handles soundboard functionality
        music_cog = Music(self)
        await self.add_cog(music_cog)
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def on_message(self, message):
        if message.author.bot:
            return
        if self.user.mentioned_in(message) and not message.mention_everyone:
            if message.author.voice:
                voice_channel = message.author.voice.channel
                voice_client = message.guild.voice_client
                if voice_client is None:
                    await voice_channel.connect()
                elif voice_channel != voice_client.channel:
                    await voice_client.move_to(voice_channel)
            else:
                await message.channel.send("You need to be in a voice channel to summon me!")
        await self.process_commands(message)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = Somalezu(
        command_prefix=commands.when_mentioned_or("/"),
        description='Assflute enjoyer',
        intents=intents,
    )
    try:
        await bot.start(TOKEN) 
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
