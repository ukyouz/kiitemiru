import os
import json
import re
import html
import time
from dotenv import load_dotenv
from contextlib import suppress
from pathlib import Path

import sqlalchemy
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from elasticsearch.helpers import BulkIndexError
from elasticsearch.exceptions import ConnectionTimeout
from sqlalchemy.orm import Session

import fastapiapp.models as models
from fastapiapp.database import SessionLocal
from fastapiapp.database import engine
from youtube.transcript import CaptionData
from youtube.transcript import SubtitleNotAvailable
from youtube.transcript import retrieve


load_dotenv()


def db_init(db: Session):
    models.Base.metadata.create_all(bind=engine)


def try_insert(db: Session, model, **kwargs):
    try:
        obj = model(**kwargs)
        db.add(obj)
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()


def insert_or_get(db: Session, model, **kwargs):
    try:
        obj = model(**kwargs)
        db.add(obj)
        db.commit()
        return obj
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        x = db.query(model).filter_by(**kwargs).first()
        assert x is not None
        return x


def store_caption(es: Elasticsearch, video_id: str, lang: str = "ja") -> bool:
    caption_file = Path("youtube/data/captions/%s.json" % video_id)
    if not caption_file.exists():
        try:
            data: list[CaptionData] = retrieve(video_id, lang=lang)
        except SubtitleNotAvailable as e:
            print(video_id, e)
            return False
    else:
        data: list[CaptionData] = json.loads(caption_file.read_text())

    filtered = []
    for c in data:
        c["text"] = re.sub(r"\[.+\]", " ", c["text"]).strip()
        if c["text"]:
            filtered.append(c)

    for c in filtered:
        c["video_id"] = video_id

    print(f"  caption count: {len(filtered)}")
    for chunk in (filtered[i : i + 600] for i in range(0, len(filtered), 600)):
        with suppress(BulkIndexError):
            try_count = 0
            while try_count < 5:
                try:
                    helpers.bulk(
                        es,
                        [
                            {
                                "_op_type": "create",
                                "_index": "captions",
                                "_id": "{}:{}".format(video_id, d["start"]),
                                "_source": d,
                            }
                            for d in chunk
                        ],
                        request_timeout=2000 + 100 * try_count,
                    )
                    break
                except ConnectionTimeout:
                    try_count += 1
                    print("--> ConnectionTimeout, wait and retry...")
            else:
                raise ConnectionTimeout()

    return True


def _yt_duration_to_seconds(duration: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if m:
        h, m, s = m.groups()
        return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)
    else:
        return 0


def store_channel(db: Session, es, cid: str, force=False) -> list[str]:
    from youtube.channel import list_videos_for_channel
    from youtube.channel import get_channel_info

    ch_cache_file = Path("youtube/data/channels/%s.json" % cid)
    if ch_cache_file.exists():
        ch_info: dict = json.loads(ch_cache_file.read_text())
    else:
        ch_info = get_channel_info(cid)
        if ch_info is None:
            print(f"{cid=} is not valid.")
            return []

    channel = insert_or_get(
        db,
        models.Channel,
        name=ch_info["snippet"]["title"],
        cid=cid,
        thumbnail=ch_info["snippet"]["thumbnails"]["default"]["url"],
        # last_sync_date=ch_info["snippet"]["publishedAt"],
    )

    ch_cache_file.write_text(json.dumps(ch_info, indent=4, ensure_ascii=False))

    # store videos
    channel_videos_cache_file = Path(f"youtube/data/videos/{cid}.json")
    if channel_videos_cache_file.exists():
        video_items: dict = json.loads(channel_videos_cache_file.read_text())

        if not force and channel.last_sync_date and video_items:
            if video_items[0]["snippet"]["publishedAt"] <= channel.last_sync_date:
                # fetch new if cached data is outdated
                video_items = list_videos_for_channel(
                    cid, until_date=channel.last_sync_date
                )
    else:
        video_items = list_videos_for_channel(cid, until_date=channel.last_sync_date)
    if len(video_items) == 0:
        return []

    channel_videos_cache_file.write_text(
        json.dumps(video_items, indent=4, ensure_ascii=False)
    )

    if not force:
        old_videos = db.query(models.Video).filter_by(channel_id=channel.ID).all()
        old_vids = [v.video_id for v in old_videos]
    else:
        old_vids = []

    videos = []
    total = len(video_items)
    for i, item in enumerate(video_items):
        if item["id"]["videoId"] in old_vids:
            continue
        snippet = item["snippet"]
        details = item["contentDetails"]

        vid = item["id"]["videoId"]
        print(f"({i + 1}/{total}) storing {vid}...")
        if not store_caption(es, item["id"]["videoId"]):
            continue

        # videos are sorted by date, newest first
        channel.last_sync_date = snippet["publishedAt"]

        try_insert(
            db,
            models.Video,
            channel_id=channel.ID,
            video_id=item["id"]["videoId"],
            title=html.unescape(snippet["title"]),
            thumbnail=snippet["thumbnails"]["medium"]["url"],
            published_at=snippet["publishedAt"],
            duration=_yt_duration_to_seconds(details["duration"]) * 1000,
        )

    db.commit()

    return [v.video_id for v in videos]


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("cid", help="channel id", default="UCmpkIzF3xFzhPez7gXOyhVg")
    parser.add_argument(
        "--force", action="store_true", help="force refetch caption data"
    )
    args = parser.parse_args()

    db = SessionLocal()
    db_init(db)
    es = Elasticsearch(
        os.getenv("ELASTIC_HOST"),
        basic_auth=(
            os.getenv("ELASTIC_USERNAME"),
            os.getenv("PASSWORD_ELASTIC"),
        ),
    )
    try:
        vids = store_channel(db, es, args.cid, args.force)
    finally:
        db.close()

    # store_caption(es, "Gjt52U9vMs4")
