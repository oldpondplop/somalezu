import asyncio
import logging
import os
from functools import wraps
from pathlib import Path

import discord
import youtube_dl
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

discord.utils.setup_logging(
    # handler=logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w'),
    level=logging.INFO,
    root=False,
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MY_GUILD = discord.Object(id=888743542510456872)

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
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
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
    
    def ensure_voice_connection(func):
        """Decorator to ensure the bot is connected to the user's voice channel before executing the command."""
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if interaction.user.voice is None:
                await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
                return 
            user_channel = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client
            if voice_client is None:
                await user_channel.connect()
            elif voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()            
                if voice_client.channel != user_channel:
                    await voice_client.move_to(user_channel)
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

    @discord.app_commands.command(name="play_local", description="Plays a file from the local filesystem")
    @discord.app_commands.describe(path="The file path to play")
    @ensure_voice_connection
    async def play_local(self, interaction: discord.Interaction, path: str):
        """Plays a file from the local filesystem"""
        await interaction.response.defer(ephemeral=True)
        fname = Path(path).name
        if not os.path.exists(path):
            await interaction.followup.send(f"The file '{fname}' does not exist.", ephemeral=True)
            return
        try:
            source = discord.FFmpegPCMAudio(path)
            if source.read() == b'':
                await interaction.followup.send(f"The file '{fname}' could not be played.", ephemeral=True)
                return
            wrapped_source = discord.PCMVolumeTransformer(source)
            interaction.guild.voice_client.play(wrapped_source, after=lambda e: print(f'Player error: {e}') if e else None)
            await interaction.followup.send(f'Now playing: {fname}', ephemeral=True)
        except Exception as e:
            logger.exception('Error in play_local command: %s', str(e))
            await interaction.response.send_message("Failed to play the requested file.", ephemeral=True)
        
    @discord.app_commands.command(name="play", description="Plays from a URL")
    @discord.app_commands.describe(url="The URL to play from")
    @ensure_voice_connection
    async def play(self, interaction: discord.Interaction, url: str):
        """Plays from a URL"""
        # Defer the response to tell Discord that the bot needs more time to process the command
        await interaction.response.defer(ephemeral=True)
        try:
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            await interaction.followup.send(f'Now playing: {player.title}', ephemeral=True)
        except Exception as e:
            logger.exception('Error in play command: %s', str(e))
            await interaction.followup.send("Failed to play the requested URL.", ephemeral=True)
    
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


class Somalezu(commands.Bot):
    def __init__(self, *, command_prefix, description, intents):
        super().__init__(command_prefix=command_prefix, intents=intents, description=description)
        # self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.add_cog(Music(self))
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

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
