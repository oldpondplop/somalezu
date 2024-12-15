import discord
from discord.ext import commands
from pathlib import Path

import discord
from discord.ext import commands
from pathlib import Path

get_env = lambda key: next((v for k, v in (l.strip().split("=", 1) for l in open(".env")) if k == key), None)
TOKEN = get_env('TOKEN')
SOUND_PATH = Path("sounds")
SUPPORTED_EXTS = {".wav", ".mp3"}
SOUND_NR = 10

intents = discord.Intents.default()
intents.message_content, intents.voice_states = True, True
bot = commands.Bot(command_prefix="!", intents=intents)
current_voice_client = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} - Soundboard ready!')

async def play_sound(ctx, sound_number):
    global current_voice_client
    sound_file = next((SOUND_PATH / f"{sound_number}{ext}" for ext in SUPPORTED_EXTS if (SOUND_PATH / f"{sound_number}{ext}").exists()), None)
    if not sound_file:
        return await ctx.send("Sound file not found.")
    if not ctx.author.voice:
        return await ctx.send("Join a voice channel to play sounds.")
    if not current_voice_client or not current_voice_client.is_connected():
        current_voice_client = await ctx.author.voice.channel.connect()
    elif current_voice_client.channel != ctx.author.voice.channel:
        await current_voice_client.move_to(ctx.author.voice.channel)
    if current_voice_client.is_playing():
        current_voice_client.stop()
    current_voice_client.play(discord.FFmpegPCMAudio(str(sound_file)), after=lambda e: print(f"Finished playing: {sound_file}"))

def create_sound_command(sound_number):
    async def command(ctx):
        await play_sound(ctx, sound_number)
    return command

for i in range(1, SOUND_NR + 1):
    bot.command(name=str(i))(create_sound_command(i))

bot.run(TOKEN)