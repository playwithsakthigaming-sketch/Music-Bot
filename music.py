import asyncio
import random
from dataclasses import dataclass
from typing import Optional

import discord
import yt_dlp


YTDL_OPTIONS = {
    "format": "bestaudio[ext=webm]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "skip_download": True,
    "extract_flat": False,
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn -loglevel warning",
}

# Queue empty ஆன பிறகு எத்தனை seconds wait பண்ண வேண்டும்.
AUTO_LEAVE_DELAY = 60


@dataclass
class Song:
    title: str
    stream_url: str
    webpage_url: str
    duration: int
    requester_id: int
    thumbnail: Optional[str] = None
    source: str = "YouTube"


class MusicPlayer:

    def __init__(self, bot):
        self.bot = bot

        self.voice: Optional[
            discord.VoiceClient
        ] = None

        self.queue: list[Song] = []

        self.current: Optional[Song] = None

        self.loop = False

        self.volume = 0.5

        self.lock = asyncio.Lock()

        self.last_error: Optional[str] = None

        # Auto leave task
        self.auto_leave_task: Optional[
            asyncio.Task
        ] = None

    # ==================================================
    # Connection
    # ==================================================

    async def connect(
        self,
        channel: discord.VoiceChannel,
    ):
        self.cancel_auto_leave()

        if self.voice and self.voice.is_connected():

            if self.voice.channel != channel:
                await self.voice.move_to(channel)

            return self.voice

        self.voice = await channel.connect(
            reconnect=True
        )

        return self.voice

    async def disconnect(self):

        self.cancel_auto_leave()

        if self.voice:

            try:

                if (
                    self.voice.is_playing()
                    or self.voice.is_paused()
                ):
                    self.voice.stop()

                await self.voice.disconnect(
                    force=True
                )

            except Exception as exc:

                print(
                    f"Disconnect error: {exc}"
                )

        self.voice = None
        self.current = None
        self.queue.clear()
        self.loop = False

    # ==================================================
    # Auto Leave
    # ==================================================

    def cancel_auto_leave(self):

        if (
            self.auto_leave_task
            and not self.auto_leave_task.done()
        ):
            self.auto_leave_task.cancel()

        self.auto_leave_task = None

    def schedule_auto_leave(self):

        self.cancel_auto_leave()

        self.auto_leave_task = (
            asyncio.create_task(
                self._auto_leave()
            )
        )

    async def _auto_leave(self):

        try:

            await asyncio.sleep(
                AUTO_LEAVE_DELAY
            )

            if not self.voice:
                return

            if not self.voice.is_connected():
                return

            # New song started while waiting.
            if (
                self.current
                or self.queue
                or self.voice.is_playing()
                or self.voice.is_paused()
            ):
                return

            print(
                "Queue empty. Auto leaving voice channel."
            )

            await self.disconnect()

        except asyncio.CancelledError:
            pass

        except Exception as exc:
            print(
                f"Auto leave error: {exc}"
            )

        finally:
            self.auto_leave_task = None

    # ==================================================
    # YouTube extraction
    # ==================================================

    async def extract_song(
        self,
        query: str,
        requester_id: int,
        source: str = "YouTube",
    ) -> Song:

        if not query.startswith(
            ("http://", "https://")
        ):
            query = f"ytsearch1:{query}"

        options = dict(YTDL_OPTIONS)

        loop = asyncio.get_running_loop()

        def extract():

            with yt_dlp.YoutubeDL(
                options
            ) as ytdl:

                return ytdl.extract_info(
                    query,
                    download=False,
                )

        info = await loop.run_in_executor(
            None,
            extract,
        )

        if not info:
            raise RuntimeError(
                "No result found."
            )

        if "entries" in info:

            entries = [
                item
                for item in info["entries"]
                if item
            ]

            if not entries:
                raise RuntimeError(
                    "No playable result found."
                )

            info = entries[0]

        stream_url = info.get("url")

        if not stream_url:
            raise RuntimeError(
                "Could not get audio stream."
            )

        return Song(
            title=info.get(
                "title",
                "Unknown title",
            ),
            stream_url=stream_url,
            webpage_url=info.get(
                "webpage_url",
                "",
            ),
            duration=info.get(
                "duration"
            ) or 0,
            requester_id=requester_id,
            thumbnail=info.get(
                "thumbnail"
            ),
            source=source,
        )

    # ==================================================
    # Duplicate Protection
    # ==================================================

    @staticmethod
    def normalize_title(
        title: str,
    ) -> str:

        return " ".join(
            title.lower().split()
        )

    def is_duplicate(
        self,
        song: Song,
    ) -> bool:

        # Check current song
        if self.current:

            if (
                song.webpage_url
                and self.current.webpage_url
                == song.webpage_url
            ):
                return True

            if (
                self.normalize_title(
                    song.title
                )
                == self.normalize_title(
                    self.current.title
                )
            ):
                return True

        # Check queue
        for queued in self.queue:

            if (
                song.webpage_url
                and queued.webpage_url
                == song.webpage_url
            ):
                return True

            if (
                self.normalize_title(
                    song.title
                )
                == self.normalize_title(
                    queued.title
                )
            ):
                return True

        return False

    async def add(
        self,
        query: str,
        requester_id: int,
        source: str = "YouTube",
    ) -> Song:

        song = await self.extract_song(
            query,
            requester_id,
            source,
        )

        if self.is_duplicate(song):

            raise ValueError(
                f"Duplicate song: {song.title}"
            )

        self.cancel_auto_leave()

        self.queue.append(song)

        return song

    # ==================================================
    # Playback
    # ==================================================

    async def start(self):

        if not self.voice:
            return

        if not self.voice.is_connected():
            return

        if (
            self.voice.is_playing()
            or self.voice.is_paused()
        ):
            return

        await self.play_next()

    def after_play(
        self,
        error,
    ):

        if error:

            print(
                f"FFmpeg/player error: {error}"
            )

        future = asyncio.run_coroutine_threadsafe(
            self.play_next(),
            self.bot.loop,
        )

        def callback(f):

            try:
                f.result()

            except Exception as exc:

                print(
                    f"Next-song error: {exc}"
                )

        future.add_done_callback(
            callback
        )

    async def play_song(
        self,
        song: Song,
    ):

        if not self.voice:
            return

        if not self.voice.is_connected():
            return

        ffmpeg = discord.FFmpegPCMAudio(
            song.stream_url,
            **FFMPEG_OPTIONS,
        )

        source = discord.PCMVolumeTransformer(
            ffmpeg,
            volume=self.volume,
        )

        self.current = song
        self.last_error = None

        self.voice.play(
            source,
            after=self.after_play,
        )

    async def play_next(self):

        while True:

            async with self.lock:

                if not self.voice:
                    return

                if not self.voice.is_connected():
                    return

                if (
                    self.voice.is_playing()
                    or self.voice.is_paused()
                ):
                    return

                # Loop current song
                if (
                    self.current
                    and self.loop
                ):

                    song = self.current

                else:

                    if not self.queue:

                        self.current = None

                        # Queue empty -> auto leave
                        self.schedule_auto_leave()

                        return

                    song = self.queue.pop(0)

                try:

                    await self.play_song(
                        song
                    )

                    return

                except Exception as exc:

                    self.last_error = str(exc)

                    print(
                        f"Playback error: {exc}"
                    )

                    self.current = None

                    # Try next queued song.
                    continue

    # ==================================================
    # Controls
    # ==================================================

    async def pause(self) -> bool:

        if (
            self.voice
            and self.voice.is_playing()
        ):

            self.voice.pause()

            return True

        return False

    async def resume(self) -> bool:

        if (
            self.voice
            and self.voice.is_paused()
        ):

            self.voice.resume()

            return True

        return False

    async def skip(self) -> bool:

        if (
            self.voice
            and (
                self.voice.is_playing()
                or self.voice.is_paused()
            )
        ):

            self.voice.stop()

            return True

        return False

    async def stop(self):

        self.loop = False
        self.queue.clear()

        if (
            self.voice
            and (
                self.voice.is_playing()
                or self.voice.is_paused()
            )
        ):

            self.voice.stop()

        self.current = None

        # Start auto leave countdown.
        if self.voice:
            self.schedule_auto_leave()

    def shuffle(self):

        random.shuffle(
            self.queue
        )

    def set_volume(
        self,
        percentage: int,
    ):

        percentage = max(
            0,
            min(
                percentage,
                100,
            ),
        )

        self.volume = (
            percentage / 100
        )

        if (
            self.voice
            and self.voice.source
            and isinstance(
                self.voice.source,
                discord.PCMVolumeTransformer,
            )
        ):

            self.voice.source.volume = (
                self.volume
            )
