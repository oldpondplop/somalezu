import asyncio
import logging
import os
from functools import wraps
from pathlib import Path

import discord
import yt_dlp as youtube_dl
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
from dotenv import load_dotenv

discord.utils.setup_logging(
    level=logging.DEBUG,
    root=True,
)
logger = logging.getLogger(__name__)

load_dotenv(override=True)
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
    # Cena variations
    '🎵': 'sounds/cena.mp3',
    '1️⃣': 'sounds/cena1.mp3',
    '2️⃣': 'sounds/cena2.mp3',
    '3️⃣': 'sounds/cena3.mp3',
    '4️⃣': 'sounds/cena4.mp3',
    '5️⃣': 'sounds/cena5.mp3',
    
    # Original mappings
    '🎹': 'sounds/cookie.mp3',
    '🥁': 'sounds/cop.mp3',
    '🎤': 'sounds/lisan.mp3',
    
    #Mario
    '🪘': 'sounds/a cazut berea.mp3',
    '🎷': 'sounds/am prins peste.mp3',
    '🎺': 'sounds/colega.mp3',
    
    # Trump
    '🎻': 'sounds/fake.mp3',
    '🎸': 'sounds/obamna.mp3',
    '⚖️': 'sounds/because-youd-be-in-jail-101soundboards.mp3',
    '🧠': 'sounds/big-brain-101soundboards.mp3',
    '🌟': 'sounds/it-was-terrifiic-101soundboards.mp3',

    # New additions
    '🧛': 'sounds/chinarespectstrumpbrain.mp3',
    '🍖': 'sounds/eatingdogs.mp3',
    
    # Previous additions
    # arnold
    '🏗️': 'sounds/construction-101soundboards.mp3',
    '🎙️': 'sounds/asking-101soundboards.mp3',
    '✅': 'sounds/correct-a-mundo-101soundboards.mp3',
    '❌': 'sounds/but-you-told-me-no-you-cant-say-no-101soundboards.mp3',
    '🤝': 'sounds/count-on-me-101soundboards.mp3',
    '💊': 'sounds/drug-101soundboards.mp3',
    '🍑': 'sounds/i-do-not-want-to-touch-his-ass-101soundboards.mp3',
    '🥷': 'sounds/ninja-101soundboards.mp3',

    # pulp
    '😱': 'sounds/fuck-what-the-fuck-101soundboards.mp3',
    '🎯': 'sounds/concentration-101soundboards.mp3',

    #
    '🦸🏽‍♂️': 'sounds/calculator-is-going-up-your-ass-tonight-101soundboards.mp3',
    '🍬': 'sounds/candy-shop-101soundboards.mp3',
    '🔫': 'sounds/does-he-look-like-a-bitch-101soundboards.mp3',
    '🇬🇧': 'sounds/english-101soundboards.mp3',
    '🙋': 'sounds/excuse-me-101soundboards.mp3',
    '🤬': 'sounds/fu-101soundboards.mp3',
    '😂': 'sounds/funny-101soundboards.mp3',
    '💭': 'sounds/had-say-101soundboards.mp3',
    '👶': 'sounds/how-we-doin-baby-101soundboards.mp3',
    '🎓': 'sounds/i-have-the-best-words-i-know-words-i-went-to-an-ivy-league-school-highly-educated-president-101soundboards.mp3',
    '🕵️': 'sounds/im-detective-john-kimble-101soundboards.mp3',
    '💣': 'sounds/im-gonna-bomb-the-sht-out-of-them-bomb-moab-isis-trump-101soundboards.mp3',
    '🙅': 'sounds/im-not-interested-in-that-101soundboards.mp3',
    '🥒': 'sounds/im-pickle-rick-101soundboards.mp3',
    '❓': 'sounds/i-want-to-ask-you-a-bunch-of-questions-and-i-want-to-ha-101soundboards.mp3',
    '📚': 'sounds/i-would-like-to-talk-to-you-about-thomas-aquinas-101soundboards.mp3',
    '💪': 'sounds/john-cena-prank-call-ringtone-101soundboards.mp3',
    '✨': 'sounds/just-do-it-101soundboards.mp3',
    '👍': 'sounds/like-101soundboards.mp3',
    '👊': 'sounds/nobody-would-be-tougher-on-isis-than-donald-trump-101soundboards.mp3',
    '🤫': 'sounds/no-talk-101soundboards.mp3',
    '📢': 'sounds/nyess-101soundboards.mp3',
    '🎮': 'sounds/pb-101soundboards.mp3',
    '😺': 'sounds/pussy2night.mp3',
    '😨': 'sounds/scream-101soundboards.mp3',
    '🔞': 'sounds/sex-101soundboards.mp3',
    '🤐': 'sounds/shut-the-fuck-up-stfu-shut-up-be-quiet-stop-talking-suck-my-dick-suck-it-101soundboards.mp3',
    '👃': 'sounds/something-smells-awfully-like-shit-101soundboards.mp3',
    '🦕': 'sounds/stegosaurus-pussy-101soundboards.mp3',
    '🚫': 'sounds/stfu-101soundboards.mp3',
    '✋': 'sounds/stop-101soundboards.mp3',
    '🛑': 'sounds/stop-it-101soundboards.mp3',
    '🌾': 'sounds/welcome-to-the-rice-fields-mother-fucker-101soundboards.mp3',
    '🔥': 'sounds/youre-fired-101soundboards.mp3',
    '📺': 'sounds/youre-the-asshole-on-tv-101soundboards.mp3',
       # Golan variations
    '🦷': 'sounds/golan1.mp3',

    # Maneaua Hackerilor variations
    '👋': 'sounds/maneauahackerilor2.mp3',
    '🦝': 'sounds/maneauahackerilor3.mp3',
    '🦊': 'sounds/maneauahackerilor4.mp3',
    '🐺': 'sounds/maneauahackerilor5.mp3',
    # Scapitanu variations
    '⚓': 'sounds/scapitanu.mp3',

    # Scap si Pajura variations
    '🦅': 'sounds/scapsipajura2.mp3',
    '🤠': 'sounds/scapsipajura3.mp3',
    '👽': 'sounds/scapsipajura.mp3',

    # Schef de Chef
    '👨‍🍳': 'sounds/schefdechef.mp3',

    # Sistemul Nr 1
    '🔢': 'sounds/sistemulnr1.mp3',

    # SMJ
    '🎤': 'sounds/sMJ.mp3',
    '👻': 'sounds/nuderanjez.mp3',
    '🪐': 'sounds/sunueversace.mp3',

    # Sună Telefoanele
    '📞': 'sounds/sunatelefoanele1.mp3',
    '👺': 'sounds/aragaz1.mp3',
    '🫥': 'sounds/aragaz2.mp3',
    '🤡': 'sounds/aragaz3.mp3',

    # New Sound Additions
    '🤣': 'sounds/catlaughing.mp3',
    '💀': 'sounds/dorianpopaciocanu.mp3',
    '🚪': 'sounds/fbiopenup.mp3',
    '⚡': 'sounds/hatzarf.mp3',
    '😱': 'sounds/manscreaming.mp3',
    '🫦': 'sounds/moan.mp3',
    '🧔': 'sounds/petre.mp3',
    '😴': 'sounds/snoremimimi.mp3',
    '🍆': 'sounds/StrokinMyD.mp3',
    '🤨': 'sounds/whathehell.mp3',
    '🦽': 'sounds/wheelchaircripling.mp3',
    '🤢': 'sounds/yuckbrothaeww.mp3',
    '📱': 'sounds/nokia.mp3',
    '🪟': 'sounds/windowsxp.mp3',
    '💉': 'sounds/sedrogheazacucocaina.mp3',
    '🦧': 'sounds/araticaomaimuta.mp3',
    '🤷‍♂️': 'sounds/vreiceas.mp3',

    # Appended New Files (previous set)
    '🐉': 'sounds/S7thelement.mp3',
    '🐲': 'sounds/Scrazyfrong.mp3',
    '🦄': 'sounds/Sgangnamstyle.mp3',
    '🌈': 'sounds/sjumatatetu.mp3',
    '🍀': 'sounds/Sketchupsong.mp3',
    '🚀': 'sounds/Smadeinromania.mp3',
    '🛸': 'sounds/SmoothOperator.mp3',
    '🧿': 'sounds/Ssaruptlantul.mp3',
    '🎆': 'sounds/Ssmoothoperator.mp3',
    '🌌': 'sounds/Sstayingalivebee.mp3',

    # Extra New Files (the ones not already added)
    '🕺': 'sounds/boratdisco.mp3',
    '🎪': 'sounds/harmanem.mp3',
    '🏃': 'sounds/staminatraining.mp3',
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

class PaginatedSoundboardView(View):
    def __init__(self, voice_client, music_cog, page=0):
        super().__init__(timeout=60)
        self.voice_client = voice_client
        self.music_cog = music_cog
        self.page = page
        self.items_per_page = 20  # Leave room for navigation buttons
        self.total_pages = (len(music_cog.soundboard_mapping) - 1) // self.items_per_page + 1
        
        # Get items for current page
        items = list(music_cog.soundboard_mapping.items())
        start_idx = self.page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_page_items = items[start_idx:end_idx]

        # Add sound buttons for current page
        for emoji, file_path in current_page_items:
            button = Button(emoji=emoji, style=discord.ButtonStyle.primary)
            button.callback = self.make_sound_callback(file_path)
            self.add_item(button)

        # Add navigation buttons
        if self.total_pages > 1:
            # Previous page button
            prev_button = Button(
                emoji="⬅️", 
                style=discord.ButtonStyle.secondary,
                disabled=self.page == 0
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

            # Page indicator button (non-functional, just shows current page)
            page_indicator = Button(
                label=f"Page {self.page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_indicator)

            # Next page button
            next_button = Button(
                emoji="➡️",
                style=discord.ButtonStyle.secondary,
                disabled=self.page == self.total_pages - 1
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    def make_sound_callback(self, file_path):
        async def play_sound(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)

            # Save the current YouTube audio state
            guild_id = interaction.guild.id
            if self.voice_client.is_playing() and guild_id in self.music_cog.current_youtube_source:
                self.music_cog.was_youtube_playing[guild_id] = True
                self.voice_client.pause()
            else:
                self.music_cog.was_youtube_playing[guild_id] = False

            def after_playback(e):
                if e:
                    logger.error(f"Soundboard playback error: {e}")
                if self.music_cog.was_youtube_playing.get(guild_id, False):
                    self.voice_client.play(self.music_cog.current_youtube_source[guild_id], after=None)

            self.voice_client.play(
                discord.FFmpegPCMAudio(file_path),
                after=after_playback
            )

        return play_sound

    async def previous_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.update_view(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.page = min(self.total_pages - 1, self.page + 1)
        await self.update_view(interaction)

    async def update_view(self, interaction: discord.Interaction):
        new_view = PaginatedSoundboardView(
            self.voice_client,
            self.music_cog,
            self.page
        )
        await interaction.response.edit_message(
            content=f"Choose a sound to play (Page {self.page + 1}/{self.total_pages}):",
            view=new_view
        )

class RadioView(View):
    def __init__(self, voice_client, music_cog):
        super().__init__(timeout=60)
        self.voice_client = voice_client
        self.music_cog = music_cog

        # Ibiza Radio Buttons
        ibiza_button = Button(
            label="Ibiza Global Radio", 
            emoji="🎵", 
            style=discord.ButtonStyle.primary
        )
        ibiza_button.callback = self.play_ibiza_radio
        self.add_item(ibiza_button)

        ibiza_classics_button = Button(
            label="Ibiza Global Classics", 
            emoji="🎼", 
            style=discord.ButtonStyle.primary
        )
        ibiza_classics_button.callback = self.play_ibiza_classics
        self.add_item(ibiza_classics_button)

# Schizoid Radio Buttons
        chillout_button = Button(
            label="Schizoid Chillout", 
            emoji="🌙", 
            style=discord.ButtonStyle.secondary
        )
        chillout_button.callback = self.play_schizoid_chill
        self.add_item(chillout_button)

        dub_button = Button(
            label="Schizoid Dub", 
            emoji="🎧", 
            style=discord.ButtonStyle.secondary
        )
        dub_button.callback = self.play_schizoid_dub
        self.add_item(dub_button)

        psy_button = Button(
            label="Schizoid Psy Trance", 
            emoji="🎹", 
            style=discord.ButtonStyle.secondary
        )
        psy_button.callback = self.play_schizoid_schizoid
        self.add_item(psy_button)

        prog_button = Button(
            label="Schizoid Progressive", 
            emoji="🎼", 
            style=discord.ButtonStyle.secondary
        )
        prog_button.callback = self.play_schizoid_psy
        self.add_item(prog_button)

    async def play_radio(self, interaction: discord.Interaction, url: str, radio_name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            
            self.voice_client.play(
                discord.FFmpegPCMAudio(url, **ffmpeg_options)
            )
            self.music_cog.current_youtube_source[interaction.guild.id] = self.voice_client.source
            
            await interaction.followup.send(f'Now playing: {radio_name} 🎶', ephemeral=True)
        except Exception as e:
            logger.exception(f'Radio playback error: {e}')
            await interaction.followup.send("Couldn't connect to the radio stream.", ephemeral=True)

    # Existing Ibiza callbacks
    async def play_ibiza_radio(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "https://listenssl.ibizaglobalradio.com:8024/ibizaglobalradio.mp3",
            "Ibiza Global Radio"
        )

    async def play_ibiza_classics(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "https://control.streaming-pro.com:8000/ibizaglobalclassics.mp3",
            "Ibiza Global Classics"
        )

    async def play_schizoid_chill(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "http://94.130.113.214:8000/chill",  # New URL format
            "Schizoid Chillout/Ambient"
        )

    async def play_schizoid_dub(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "http://94.130.113.214:8000/dubtechno",    # New URL format
            "Schizoid Dub Techno"
        )

    async def play_schizoid_schizoid(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "http://94.130.113.214:8000/schizoid",    # New URL format
            "Schizoid Psy Trance"
        )

    async def play_schizoid_psy(self, interaction: discord.Interaction):
        await self.play_radio(
            interaction,
            "http://94.130.113.214:8000/prog",    # New URL format
            "Schizoid Progressive"
        )


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.soundboard_mapping = SOUNDBOARD_MAPPING
        self.current_youtube_source = {}  # To store the current YouTube audio source per guild
        self.was_youtube_playing = {}  # To track if YouTube audio was playing before soundboard

    @discord.app_commands.command(name="play", description="Plays from a URL")
    @discord.app_commands.describe(url="The URL to play from")
    @ensure_voice_connection
    async def play(self, interaction: discord.Interaction, url: str):
        """Streams audio from a URL"""
        await interaction.response.defer(ephemeral=True)
        try:
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
            
            voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            self.current_youtube_source[interaction.guild.id] = player
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
            if guild_id in self.current_youtube_source:
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
        """Displays a paginated soundboard with buttons for each sound."""
        view = PaginatedSoundboardView(interaction.guild.voice_client, self)
        await interaction.response.send_message("Choose a sound to play:", view=view, ephemeral=True)

    @discord.app_commands.command(name="radio", description="Play Ibiza Global Radio stations")
    @ensure_voice_connection
    async def radio(self, interaction: discord.Interaction):
        """Displays radio station buttons and plays selected station"""
        view = RadioView(interaction.guild.voice_client, self)
        await interaction.response.send_message("Choose a radio station:", view=view, ephemeral=True)
            
class Somalezu(commands.Bot):
    def __init__(self, *, command_prefix, description, intents):
        super().__init__(command_prefix=command_prefix, intents=intents, description=description)

    async def setup_hook(self):
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
        print('------',TOKEN)
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