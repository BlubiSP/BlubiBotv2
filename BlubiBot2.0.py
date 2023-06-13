import discord, os, random
from json import dumps, load
from typing import Literal
from asyncio import run_coroutine_threadsafe
from datetime import datetime as dt

SONGLIST_PATH = "C:/Users/stefa/Desktop/python/BlubiBotv2/"
MUSIC_PATH = "C:/Users/stefa/Music/"
FFMPEG_PATH = "C:/Users/stefa/Desktop/python/BlubiBotv2/ffmpeg.exe"
# % chance for favorited songs to play
FAVORITE_CHANCE = 10
GUILD_ID = 1099352065702101064
###testing
MAIN_GUILD = 124792011487313924
TEST_GUILD = 1099352065702101064
###

with open("Bot_Token.txt", "r") as file:
    BOT_TOKEN = file.read()

  

class MyClient(discord.Client):
    def __init__(self, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        #await self.tree.sync()
        print("I am ready!")

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))


intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = MyClient(intents = intents)


playlist = []
favorite = []
last5  = []
current_song = None


@client.tree.command(name = "load_folder", guild=discord.Object(id=GUILD_ID))
async def load_folder(interaction: discord.Interaction):
    """ Load Songs from MUSIC_PATH into playlist.json"""

    print("Checking if playlist.json exists...")
    if os.path.exists(f"{SONGLIST_PATH}playlist.json"):
        print("It does...")
        song_dict = load_json()

    else:
        print("It does not....")
        song_dict = {}
        
    #creates a list of all files that end in .mp3 or .webm in MUSIC_PATH
    song_list = [song for song in os.listdir(MUSIC_PATH) if ".mp3" in song or ".webm" in song]
    count = 0

    print("Loading new songs...")
    for song_name in song_list:
        if song_name not in song_dict.keys():
            song_dict[song_name] = {"last_played" : "never",
            "favorite" : False,
            "skipped" : 0,
            "location" : MUSIC_PATH + song_name}
            count += 1
            print(f"Added {song_name}")
        else:
            print(f"Duplicate found: {song_name} Skipping...")

    with open(f"{SONGLIST_PATH}playlist.json", "w") as file:
        file.write(dumps(song_dict))
    
    if count > 0:    
        await interaction.response.send_message(f"""
            Added {count} new Songs!
        """)
    else:
        await interaction.response.send_message("No new songs found.")


@client.tree.command(name = "verify_playlist",guild=discord.Object(id=GUILD_ID))     
async def verify_playlist(interaction: discord.Interaction):
    """Verify that all songs from playlist.json are also in MUSIC_PATH. CAUTION this deletes all entries from playlist.json that are not in the current MUSIC_PATH"""

    await interaction.response.send_message("Checking if playlist and MUSIC_PATH match...")
    song_dict = load_json()
    song_list = [song for song in os.listdir(MUSIC_PATH) if ".mp3" in song or ".webm" in song]
    missing_songs = [song for song in song_dict.keys() if song not in song_list]
    if missing_songs:
        for song in missing_songs:
            print(f"Deleted{song}")
            del song_dict[song]
        return await interaction.followup.send(f"Found {len(missing_songs)} songs that are in playlist.json but not in MUSIC_PATH and deleted them.")  
    return await interaction.followup.send("Everything is fine.")
        


@client.tree.command(name = "play", guild=discord.Object(id=GUILD_ID))
async def play(interaction: discord.Interaction, category: Literal["new", "all", "favorite"]):
    """Start playing Music. Make sure to use /join first!"""

    global playlist, favorite
    song_dict = load_json()
    if len(song_dict) == 0:
        return await interaction.response.send_message("No songs in playlist\nUse /load_folder to load songs")
    
    if not interaction.guild.voice_client:
        return await interaction.response.send_message("Use /join first")
    
    if interaction.guild.voice_client.is_playing():
        return await interaction.response.send_message("Already playing audio.")

    if category == "favorite":
        await interaction.response.send_message("Loaded Favorites")
        playlist = [song for song in song_dict if song_dict[song]["favorite"] == True]
    
    elif category == "new":
        await interaction.response.send_message("Loaded new")
        playlist = [song for song in song_dict if song_dict[song]["last_played"] == "never"]
        # new also plays favorites. If you want new to only play new songs comment out the line below
        favorite = [song for song in song_dict if song_dict[song]["favorite"] == True]
    
    else:
        await interaction.response.send_message("Loaded all")
        favorite = [song for song in song_dict if song_dict[song]["favorite"] == True]
        playlist = [song for song in song_dict]

    random.shuffle(playlist)

    await interaction.followup.send(f"Playing {len(playlist)} Songs")
    try:
        await play_song(interaction.guild.voice_client)
    except discord.ClientException as e:
        await interaction.followup.send(f"{e}\nBot is now desynced please restart it")


@client.tree.command(name = "favorite", guild=discord.Object(id=GUILD_ID))
async def favorite(interaction: discord.Interaction):
    """Favorite the current song to increase the chance of it playing again!"""
    song_dict = load_json()
    if current_song:
        with open(SONGLIST_PATH + "playlist.json", "w") as file:
            song_dict[current_song]["favorite"] = True
            file.write(dumps(song_dict))
        return await interaction.response.send_message(f"{current_song} added to favorites")
    return await interaction.response.send_message("I haven't played anything yet")


@client.tree.command(name = "current", guild=discord.Object(id=GUILD_ID))
async def current(interaction: discord.Interaction):
    """Tells you the name of the current or last song played"""
    if current_song:
        return await interaction.response.send_message(f"Current or last song is: {current_song}")
    return await interaction.response.send_message("I haven't played anything yet")


@client.tree.command(name = "songname", guild=discord.Object(id=GUILD_ID))
async def songname(interaction: discord.Interaction):
    """Tells you the name of the current or last song played"""
    if interaction.guild.voice_client.is_playing():
        return await interaction.response.send_message(f"Current or last song is: {current_song}")
    return await interaction.response.send_message("I am not playing anything.")

@client.tree.command(name = "skip", guild=discord.Object(id=GUILD_ID))
async def skip(interaction: discord.Interaction):
    """Skips current song"""
    try:
        if interaction.guild.voice_client.is_playing():
            song_dict = load_json()
            with open(SONGLIST_PATH + "playlist.json", "w") as file:
                song_dict[current_song]["skipped"] += 1
                file.write(dumps(song_dict))
            interaction.guild.voice_client.stop()
            return await interaction.response.send_message(f"{current_song} skipped")
        return await interaction.response.send_message("I am not playing anything.")
    except AttributeError:
        await interaction.response.send_message("I am not in a voice chat.")


@client.tree.command(name = "pause", guild=discord.Object(id=GUILD_ID))
async def pause(interaction: discord.Interaction):
    """Pauses current song"""
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        return await interaction.response.send_message(f"Paused")
    return await interaction.response.send_message("I am not playing anything.")


@client.tree.command(name = "resume", guild=discord.Object(id=GUILD_ID))
async def resume(interaction: discord.Interaction):
    """Resumes current song"""
    if interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        return await interaction.response.send_message(f"resuming")
    return await interaction.response.send_message("I am not paused.")


@client.tree.command(name = "last", guild=discord.Object(id=GUILD_ID))
async def next_songs(interaction: discord.Interaction):
    """Shows the last 5 Songs"""
    if last5:
        response = f"Here are the last {len(last5)} songs:\n"
        for song in last5:
            response += song + "\n"
        return await interaction.response.send_message(response)
        
    await interaction.response.send_message("There are no played songs")


@client.tree.command(name = "next_songs", guild=discord.Object(id=GUILD_ID))
async def next_songs(interaction: discord.Interaction, number_of_songs : int = 5):
    """Shows the next number of songs. Default 5"""
    if playlist:
        count = 0
        response = f"\n"
        for n in range(number_of_songs):
            try:
                response += playlist[n] + "\n"
                count +=1
            except IndexError as e:
                print(e)
        return await interaction.response.send_message(f"Here are the next {count} songs:" + response)
        
    await interaction.response.send_message("Playlist is empty.")


@client.tree.command(name = "join", guild=discord.Object(id=GUILD_ID))
async def join(interaction: discord.Interaction):
    """Join the voice channel"""
    global voice_client
    channel = interaction.user.voice.channel
    try:
        await channel.connect(self_deaf=True, reconnect=True, timeout=30)
        voice_client = interaction.guild.voice_client
        await interaction.response.send_message("Hello! Use /play to play music!")
    except discord.ClientException as e:
        await interaction.response.send_message(e)


@client.tree.command(name = "dc", guild=discord.Object(id=GUILD_ID))
async def dc(interaction: discord.Interaction):
    """Disconnect from the voice channel"""
    global voice_client
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        voice_client = None
        return await interaction.response.send_message("Bye!")
    #testing
    return await interaction.response.send_message("I am not connected to any voice channel on this server!")


#testing
@client.tree.command(name = "test", guild=discord.Object(id=GUILD_ID))
async def test(interaction: discord.Interaction):
    """For testing only. Most likely does nothing"""
    return await interaction.response.send_message("Nothing")


async def play_song(voice_client):
    global current_song, last5
    if len(playlist) == 0:
        return
    
    #roll for favorite
    roll = random.randint(1, 100)
    if roll < FAVORITE_CHANCE and len(favorite) > 0:
        print("Picking from Favorites")
        current_song = favorite.pop(0)
    else:
        print("Picking from playlist")
        current_song = playlist.pop(0)

    #update last5 played songs
    if len(last5) < 5:
        last5.append(current_song)
    else:
        last5.pop(0)
        last5.append(current_song)
    
    #play song
    print(f"Now playing: {current_song}")
    song_dict = load_json()
    with open(SONGLIST_PATH + "playlist.json", "w") as file:
        song_dict[current_song]["last_played"] = dt.now().strftime("%d/%m/%Y, %H:%M")
        file.write(dumps(song_dict))
    songFilePath = MUSIC_PATH + current_song
    source = discord.FFmpegPCMAudio(source = songFilePath, executable = FFMPEG_PATH ,options="-b:a 128k")
    voice_client.play(source, after=dispatch_play_song)


def dispatch_play_song(e):
    if e is not None:
        print("Error: ", end="")
        print(e)
        return

    coro = play_song(voice_client)
    fut = run_coroutine_threadsafe(coro, client.loop)
    try:
        fut.result()
    except:
        pass

    return


def load_json():
    if os.path.exists(f"{SONGLIST_PATH}playlist.json"):
        with open(SONGLIST_PATH + "playlist.json", "r", encoding="UTF-8") as file:
            song_dict = load(file)
        return song_dict
    return {}


client.run(BOT_TOKEN) 
           #log_handler=None)