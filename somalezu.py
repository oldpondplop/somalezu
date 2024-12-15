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
        


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id:
            return
        if before.channel is None or after.channel is None:
            return
        if before.channel != after.channel:
            voice_client = after.channel.guild.voice_client
            if voice_client:
                await voice_client.move_to(after.channel)
                if voice_client.is_playing():
                    voice_client.pause()
                    await self._retry_resuming(voice_client)
    
    async def _retry_resuming(self, voice_client, attempts=5):
        for _ in range(attempts):
            await asyncio.sleep(0.5)
            if voice_client.is_connected():
                if voice_client.is_paused():
                    voice_client.resume()
                    return

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
    
    @app_commands.command(name="ping", description="Returns the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {self.bot.latency * 1000:.0f} ms")
    
    @app_commands.command(name="join", description="Joins a voice channel")
    @app_commands.describe(channel="The voice channel to join")
    async def join(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"Connected to {channel.name}", ephemeral=True)
    
    @discord.app_commands.command(name="play", description="Plays from a URL")
    @discord.app_commands.describe(url="The URL to play from")
    @ensure_voice_connection
    async def play(self, interaction: discord.Interaction, url: str):
        """Streams audio from a URL"""
        await interaction.response.defer(ephemeral=True)
        try:
            # Stream flag is set to True to enable streaming
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
            voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            await interaction.followup.send(f'Now streaming: {player.title}', ephemeral=True)
        except Exception as e:
            logger.exception('Error in stream command: %s', str(e))
            await interaction.followup.send("Failed to stream the requested URL.", ephemeral=True)

    @discord.app_commands.command(name="resume", description="Resumes paused audio playback")
    @ensure_voice_connection
    async def resume(self, interaction: discord.Interaction):
        """Resumes the currently paused audio"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Playback resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio is currently paused.", ephemeral=True)

    @discord.app_commands.command(name="pause", description="Pauses the current audio playback")
    @ensure_voice_connection
    async def pause(self, interaction: discord.Interaction):
        """Pauses the currently playing audio"""
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Playback paused.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio is currently playing.", ephemeral=True)

    @discord.app_commands.command(name="stop", description="Stops the currently playing audio")
    @ensure_voice_connection
    async def stop(self, interaction: discord.Interaction):
        """Stops the currently playing or paused audio"""
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message("Playback stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio is currently playing.", ephemeral=True)

class SoundboardView(View):
    def __init__(self, voice_client):
        super().__init__(timeout=60)  # Timeout after 60 seconds of inactivity
        self.voice_client = voice_client

        for emoji, file_path in SOUNDBOARD_MAPPING.items():
            button = Button(emoji=emoji, style=discord.ButtonStyle.primary)
            button.callback = self.make_sound_callback(file_path)
            self.add_item(button)

    def make_sound_callback(self, file_path):
        async def play_sound(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)    
            if not Path(file_path).exists():
                print(f"Sound file not found: {file_path}")
                await interaction.response.send_message("Sound file not found!", ephemeral=True)
                return

            if self.voice_client.is_playing():
                self.voice_client.stop()

            self.voice_client.play(discord.FFmpegPCMAudio(file_path), after=lambda e: logger.error(f"Playback error: {e}") if e else None)
        return play_sound

class Soundboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.soundboard = SOUNDBOARD_MAPPING

    def ensure_voice_connection(func):
        """Decorator to ensure the bot is connected to the user's voice channel."""
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if interaction.user.voice is None:
                await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
                return
            if interaction.guild.voice_client is None:
                await interaction.user.voice.channel.connect()
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    
    @app_commands.command(name="soundboard", description="Select and play a sound from the soundboard")
    @ensure_voice_connection
    async def soundboard(self, interaction: discord.Interaction):
        """Displays a soundboard with buttons for each sound."""
        view = SoundboardView(interaction.guild.voice_client)
        await interaction.response.send_message("Choose a sound to play:", view=view, ephemeral=True)

class Somalezu(commands.Bot):
    def __init__(self, *, command_prefix, description, intents):
        super().__init__(command_prefix=command_prefix, intents=intents, description=description)

    async def setup_hook(self):
        music_cog = Music(self)
        soundboard_cog = Soundboard(self)
        await self.add_cog(music_cog)
        await self.add_cog(soundboard_cog)
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
