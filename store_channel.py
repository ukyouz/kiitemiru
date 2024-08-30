import json
import html
import sqlite3
from pathlib import Path
from contextlib import suppress
from dataclasses import dataclass

from db.sqlite3 import Sqlite, UniqueStr


@dataclass
class Channel:
    name: str
    cid: UniqueStr
    thumbnail: str
    last_sync_date: str


@dataclass
class Video:
    channel_id: int
    video_id: UniqueStr
    title: str
    thumbnail: str
    published_at: str
    __foreigns__ = (
        ("channel_id", "Channel(cid)"),
    )


def fetch_video(channel_id: str, dbid: int) -> list[Video]:
    # TODO: use api
    with open("youtube/data/videos/%s.json" % channel_id) as fs:
        ch_info: dict = json.load(fs)

    videos = []
    for item in ch_info["items"]:
        snippet = item["snippet"]
        videos.append(
            Video(
                channel_id=dbid,
                video_id=item["id"]["videoId"],
                title=html.unescape(snippet["title"]),
                thumbnail=snippet["thumbnails"]["default"]["url"],
                published_at=snippet["publishedAt"],
            )
        )
    return videos


def save_transcript(video_id: str, lang: str = "ja"):
    from youtube import transcript
    cap_file = Path("youtube/data/captions/%s.json" % video_id)
    if cap_file.exists():
        return
    captions = transcript.retrieve(video_id, lang=lang)
    with open(cap_file, "w") as fs:
        fs.write(json.dumps(captions, indent=4, ensure_ascii=False))


def init_database():
    with Sqlite("data.db") as db:
        db.drop_table(Channel)
        db.create_table(Channel)

        db.drop_table(Video)
        db.create_table(Video)


def main(ch_info: dict):
    snippet = ch_info["snippet"]
    channel = Channel(
        name=snippet["title"],
        cid=snippet["channelId"],
        thumbnail=snippet["thumbnails"]["default"]["url"],
        last_sync_date=snippet["publishedAt"],
    )
    with Sqlite("data.db") as db:
        id = db.insert_row(channel, exists_ok=True)
        videos = fetch_video(channel.cid, id)
        for v in videos:
            save_transcript(v.video_id)
            with suppress(sqlite3.IntegrityError):
                db.insert_row(v)

        # db.insert_rows(Video, videos)


if __name__ == "__main__":
    # init_database()
    cid = "UCmpkIzF3xFzhPez7gXOyhVg"
    with open("youtube/data/channels/%s.json" % cid) as fs:
        ch_info: dict = json.load(fs)
    main(ch_info)

