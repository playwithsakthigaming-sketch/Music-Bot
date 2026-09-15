import asyncio
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from music import MusicPlayer
from spotify import SpotifyManager


load_dotenv()


TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

SPOTIFY_CLIENT_ID = os.getenv(
    "SPOTIFY_CLIENT_ID"
)

SPOTIFY_CLIENT_SECRET = os.getenv(
    "SPOTIFY_CLIENT_SECRET"
)

GUILD_ID = os.getenv(
    "GUILD_ID"
)


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing."
    )


intents = discord.Intents.default()


class MusicBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.players: dict[
            int,
            MusicPlayer,
        ] = {}

        self.spotify = SpotifyManager(
            SPOTIFY_CLIENT_ID,
            SPOTIFY_CLIENT_SECRET,
        )

    def get_player(
        self,
        guild_id: int,
    ) -> MusicPlayer:

        if guild_id not in self.players:
            self.players[guild_id] = (
                MusicPlayer(self)
            )

        return self.players[guild_id]

    async def setup_hook(self):

        if GUILD_ID:

            guild = discord.Object(
                id=int(GUILD_ID)
            )

            self.tree.copy_global_to(
                guild=guild
            )

            await self.tree.sync(
                guild=guild
            )

            print(
                "Slash commands synced "
                f"to guild {GUILD_ID}"
            )

        else:

            await self.tree.sync()

            print(
                "Global slash commands synced."
            )

    async def on_ready(self):

        print(
            f"Logged in as "
            f"{self.user} "
            f"(ID: {self.user.id})"
        )

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            )
        )


bot = MusicBot()


# ==================================================
# Helpers
# ==================================================


def get_voice_channel(
    interaction: discord.Interaction,
) -> Optional[discord.VoiceChannel]:

    member = interaction.user

    if not isinstance(
        member,
        discord.Member,
    ):
        return None

    if not member.voice:
        return None

    channel = member.voice.channel

    if isinstance(
        channel,
        discord.VoiceChannel,
    ):
        return channel

    return None


async def get_player_for_interaction(
    interaction: discord.Interaction,
) -> Optional[MusicPlayer]:

    if not interaction.guild:
        await interaction.followup.send(
            "❌ This command can only be used in a server."
        )
        return None

    channel = get_voice_channel(
        interaction
    )

    if not channel:
        await interaction.followup.send(
            "❌ First join a voice channel."
        )
        return None

    player = bot.get_player(
        interaction.guild.id
    )

    try:
        await player.connect(channel)

    except Exception as exc:

        await interaction.followup.send(
            "❌ I couldn't join your "
            f"voice channel.\n`{exc}`"
        )

        return None

    return player


def format_time(seconds: int) -> str:

    if not seconds:
        return "Unknown"

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return (
            f"{hours}:{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:{seconds:02d}"
    )


def spotify_embed(
    title: str,
    artist: str,
    source: str,
):
    embed = discord.Embed(
        title="🎧 Spotify",
        description=(
            f"**{title}**\n"
            f"by {artist}"
        ),
    )

    embed.add_field(
        name="Source",
        value=source,
        inline=True,
    )

    return embed


# ==================================================
# Player buttons
# ==================================================


class PlayerView(discord.ui.View):

    def __init__(
        self,
        guild_id: int,
    ):
        super().__init__(
            timeout=300
        )

        self.guild_id = guild_id

    def player(self):
        return bot.get_player(
            self.guild_id
        )

    @discord.ui.button(
        emoji="⏸️",
        style=discord.ButtonStyle.primary,
    )
    async def pause_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        player = self.player()

        if await player.pause():
            await interaction.response.send_message(
                "⏸️ Paused.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Nothing is playing.",
                ephemeral=True,
            )

    @discord.ui.button(
        emoji="▶️",
        style=discord.ButtonStyle.success,
    )
    async def resume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        player = self.player()

        if await player.resume():
            await interaction.response.send_message(
                "▶️ Resumed.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Music isn't paused.",
                ephemeral=True,
            )

    @discord.ui.button(
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
    )
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        player = self.player()

        if await player.skip():
            await interaction.response.send_message(
                "⏭️ Skipped.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Nothing is playing.",
                ephemeral=True,
            )

    @discord.ui.button(
        emoji="🔀",
        style=discord.ButtonStyle.secondary,
    )
    async def shuffle_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        player = self.player()

        if len(player.queue) < 2:
            await interaction.response.send_message(
                "❌ Need at least 2 queued songs.",
                ephemeral=True,
            )
            return

        player.shuffle()

        await interaction.response.send_message(
            "🔀 Queue shuffled.",
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="🔁",
        style=discord.ButtonStyle.secondary,
    )
    async def loop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):

        player = self.player()

        player.loop = not player.loop

        status = (
            "enabled"
            if player.loop
            else "disabled"
        )

        await interaction.response.send_message(
            f"🔁 Loop {status}.",
            ephemeral=True,
        )


# ==================================================
# /play
# ==================================================


@bot.tree.command(
    name="play",
    description=(
        "Play YouTube music or Spotify tracks"
    ),
)
@app_commands.describe(
    query=(
        "YouTube URL/search or Spotify URL"
    )
)
async def play(
    interaction: discord.Interaction,
    query: str,
):

    await interaction.response.defer()

    player = await get_player_for_interaction(
        interaction
    )

    if not player:
        return

    query = query.strip()

    # ----------------------------------------------
    # Spotify
    # ----------------------------------------------

    if bot.spotify.is_spotify_url(query):

        if not bot.spotify.configured:

            await interaction.followup.send(
                "❌ Spotify isn't configured.\n"
                "Add `SPOTIFY_CLIENT_ID` and "
                "`SPOTIFY_CLIENT_SECRET` "
                "in Railway Variables."
            )

            return

        try:

            content_type, tracks = (
                await asyncio.to_thread(
                    bot.spotify.resolve,
                    query,
                )
            )

        except Exception as exc:

            await interaction.followup.send(
                "❌ Spotify error:\n"
                f"`{exc}`"
            )

            return

        if not tracks:

            await interaction.followup.send(
                "❌ No playable Spotify tracks found."
            )

            return

        # Safety limit for huge playlists.
        max_tracks = 100

        original_count = len(tracks)

        tracks = tracks[:max_tracks]

        if original_count > max_tracks:
            note = (
                f"\n⚠️ Playlist limited to "
                f"{max_tracks} tracks."
            )
        else:
            note = ""

        message = await interaction.followup.send(
            f"🎧 Spotify **{content_type}** found.\n"
            f"🔎 Searching YouTube for "
            f"**{len(tracks)}** track(s)..."
            f"{note}"
        )

        added = 0

        for track in tracks:

            try:

                await player.add(
                    track["query"],
                    interaction.user.id,
                    source="Spotify",
                )

                added += 1

            except Exception as exc:

                print(
                    "Spotify → YouTube error: "
                    f"{track['query']} | {exc}"
                )

        if added == 0:

            await message.edit(
                content=(
                    "❌ None of the Spotify "
                    "tracks could be found "
                    "on YouTube."
                )
            )

            return

        await message.edit(
            content=(
                f"✅ Added **{added}** "
                f"Spotify track(s) to queue."
            )
        )

    # ----------------------------------------------
    # YouTube
    # ----------------------------------------------

    else:

        try:

            song = await player.add(
                query,
                interaction.user.id,
                source="YouTube",
            )

        except Exception as exc:

            await interaction.followup.send(
                "❌ YouTube error:\n"
                f"`{exc}`"
            )

            return

        embed = discord.Embed(
            title="🎵 Added to Queue",
            description=(
                f"**{song.title}**"
            ),
        )

        embed.add_field(
            name="Duration",
            value=format_time(
                song.duration
            ),
            inline=True,
        )

        embed.add_field(
            name="Source",
            value=song.source,
            inline=True,
        )

        if song.thumbnail:
            embed.set_thumbnail(
                url=song.thumbnail
            )

        await interaction.followup.send(
            embed=embed,
            view=PlayerView(
                interaction.guild.id
            ),
        )

    await player.start()


# ==================================================
# /pause
# ==================================================


@bot.tree.command(
    name="pause",
    description="Pause current music",
)
async def pause(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    if await player.pause():

        await interaction.followup.send(
            "⏸️ Music paused."
        )

    else:

        await interaction.followup.send(
            "❌ Nothing is playing."
        )


# ==================================================
# /resume
# ==================================================


@bot.tree.command(
    name="resume",
    description="Resume paused music",
)
async def resume(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    if await player.resume():

        await interaction.followup.send(
            "▶️ Music resumed."
        )

    else:

        await interaction.followup.send(
            "❌ Music isn't paused."
        )


# ==================================================
# /skip
# ==================================================


@bot.tree.command(
    name="skip",
    description="Skip current song",
)
async def skip(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    if await player.skip():

        await interaction.followup.send(
            "⏭️ Skipped."
        )

    else:

        await interaction.followup.send(
            "❌ Nothing is playing."
        )


# ==================================================
# /stop
# ==================================================


@bot.tree.command(
    name="stop",
    description="Stop music and clear queue",
)
async def stop(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    await player.stop()

    await interaction.followup.send(
        "⏹️ Stopped and cleared the queue."
    )


# ==================================================
# /leave
# ==================================================


@bot.tree.command(
    name="leave",
    description="Leave voice channel",
)
async def leave(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    await player.disconnect()

    await interaction.followup.send(
        "👋 Left the voice channel."
    )


# ==================================================
# /queue
# ==================================================


@bot.tree.command(
    name="queue",
    description="Show the music queue",
)
async def queue(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="📜 Music Queue"
    )

    if player.current:

        embed.add_field(
            name="▶️ Now Playing",
            value=(
                f"**{player.current.title}**\n"
                f"`{format_time(player.current.duration)}`"
            ),
            inline=False,
        )

    if not player.queue:

        if not player.current:
            embed.description = (
                "The queue is empty."
            )

        await interaction.followup.send(
            embed=embed
        )

        return

    songs = []

    for index, song in enumerate(
        player.queue[:20],
        start=1,
    ):

        songs.append(
            f"`{index}.` "
            f"**{song.title}** "
            f"`{format_time(song.duration)}`"
        )

    if len(player.queue) > 20:

        songs.append(
            f"\n...and "
            f"{len(player.queue) - 20} "
            f"more."
        )

    embed.add_field(
        name=(
            f"Up Next "
            f"({len(player.queue)})"
        ),
        value="\n".join(songs),
        inline=False,
    )

    await interaction.followup.send(
        embed=embed
    )


# ==================================================
# /shuffle
# ==================================================


@bot.tree.command(
    name="shuffle",
    description="Shuffle the queue",
)
async def shuffle(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    if len(player.queue) < 2:

        await interaction.followup.send(
            "❌ Need at least 2 songs."
        )

        return

    player.shuffle()

    await interaction.followup.send(
        "🔀 Queue shuffled."
    )


# ==================================================
# /loop
# ==================================================


@bot.tree.command(
    name="loop",
    description="Toggle current-song loop",
)
async def loop(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    player.loop = not player.loop

    if player.loop:
        text = "🔁 Loop enabled."
    else:
        text = "➡️ Loop disabled."

    await interaction.followup.send(
        text
    )


# ==================================================
# /volume
# ==================================================


@bot.tree.command(
    name="volume",
    description="Set volume from 0 to 100",
)
@app_commands.describe(
    level="Volume percentage"
)
async def volume(
    interaction: discord.Interaction,
    level: app_commands.Range[
        int,
        0,
        100,
    ],
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    player.set_volume(level)

    await interaction.followup.send(
        f"🔊 Volume: **{level}%**"
    )


# ==================================================
# /nowplaying
# ==================================================


@bot.tree.command(
    name="nowplaying",
    description="Show current song",
)
async def nowplaying(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    song = player.current

    if not song:

        await interaction.followup.send(
            "❌ Nothing is playing."
        )

        return

    embed = discord.Embed(
        title="🎵 Now Playing",
        description=(
            f"**{song.title}**"
        ),
    )

    embed.add_field(
        name="Duration",
        value=format_time(
            song.duration
        ),
        inline=True,
    )

    embed.add_field(
        name="Source",
        value=song.source,
        inline=True,
    )

    if song.webpage_url:

        embed.add_field(
            name="YouTube",
            value=song.webpage_url,
            inline=False,
        )

    if song.thumbnail:
        embed.set_thumbnail(
            url=song.thumbnail
        )

    await interaction.followup.send(
        embed=embed,
        view=PlayerView(
            interaction.guild.id
        ),
    )


# ==================================================
# /clear
# ==================================================


@bot.tree.command(
    name="clear",
    description="Clear queued songs",
)
async def clear(
    interaction: discord.Interaction,
):

    await interaction.response.defer()

    if not interaction.guild:
        return

    player = bot.get_player(
        interaction.guild.id
    )

    count = len(player.queue)

    player.queue.clear()

    await interaction.followup.send(
        f"🗑️ Cleared **{count}** queued song(s)."
    )


# ==================================================
# Error handler
# ==================================================


@bot.tree.error
async def command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):

    print(
        f"Command error: {error}"
    )

    message = (
        "❌ Something went wrong.\n"
        f"`{error}`"
    )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True,
            )

    except Exception:
        pass


# ==================================================
# Start bot
# ==================================================


if __name__ == "__main__":
    bot.run(TOKEN)
