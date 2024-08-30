import logging
from collections import defaultdict
from datetime import timedelta
from dataclasses import asdict

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql import functions

from fastapiapp import models
from fastapiapp import schemas
from fastapiapp.database import ElasticDb


logger = logging.getLogger(__name__)
# def get_channel(db: Session, channel_id: str):
#     return db.query(models.Channel).filter(models.Channel.cid == channel_id).first()


# def create_channel(db: Session, channel: schemas.ChannelCreate):
#     db_channel = models.Channel(name=channel.name, description=channel.description)
#     db.add(db_channel)
#     db.commit()
#     db.refresh(db_channel)
#     return db_channel


# def get_video(db: Session, video_id: int):
#     return db.query(models.Video).filter(models.Video.id == video_id).first()


# def create_video(db: Session, video: schemas.VideoCreate, channel_id: int):
#     db_video = models.Video(
#         title=video.title, description=video.description, channel_id=channel_id
#     )
#     db.add(db_video)
#     db.commit()
#     db.refresh(db_video)
#     return db_video


# def get_captions(db: Session, video_id: str):
#     return [
#         x[0]
#         for x in db.query(models.Caption, models.Video)
#         .filter(models.Video.video_id == video_id)
#         .all()
#     ]


def int_from_decimal(decimal_instance):
    list_d = str(decimal_instance).split(".")

    if len(list_d) == 2:
        # Negative exponent
        exponent = -len(list_d[1])
        integer = int(list_d[0] + list_d[1])

    else:
        str_dec = list_d[0].rstrip("0")
        # Positive exponent
        exponent = len(list_d[0]) - len(str_dec)
        integer = int(str_dec)

    return integer * (10**exponent)


def get_channels(db: Session):
    channels = db.query(models.Channel).all()
    if channels == []:
        return {
            "summary": {
                "total_duration": "00:00:00",
            },
            "items": [],
        }

    total_ms = db.query(functions.sum(models.Video.duration)).scalar()

    total_ms = int_from_decimal(total_ms)
    total_duration = timedelta(milliseconds=total_ms)
    total_duration -= timedelta(microseconds=total_duration.microseconds)

    infos = []
    for c in channels:
        info = {
            "id": c.cid,
            "name": c.name,
            "thumbnail": c.thumbnail,
            "last_sync_date": c.last_sync_date,
            # "videos": channel_vids[c.ID],
        }
        infos.append(info)

    return {
        "summary": {
            "total_duration": str(total_duration),
        },
        "items": infos,
    }


def get_videos(db: Session, channel_id: str):
    c = db.query(models.Channel).filter(models.Channel.cid == channel_id).first()
    if c is None:
        return {
            "error": "Channel not found",
        }

    videos = db.query(models.Video).filter(models.Video.channel_id == c.ID).all()

    total_sec = sum(v.duration for v in videos)
    total_duration = timedelta(milliseconds=total_sec)
    total_duration -= timedelta(microseconds=total_duration.microseconds)

    return {
        "id": c.cid,
        "name": c.name,
        "thumbnail": c.thumbnail,
        "last_sync_date": c.last_sync_date,
        "total_duration": str(total_duration),
        "videos": [
            {
                "id": v.video_id,
                "title": v.title,
                "thumbnail": v.thumbnail,
                "published_at": v.published_at,
            }
            for v in videos
        ],
    }


def _sort_captions_by_video(db: Session, hits: dict) -> list[dict]:
    vids = set(hit["_source"]["video_id"] for hit in hits["hits"])

    channel_videos = (
        db.query(models.Channel, models.Video)
        .join(models.Video, models.Channel.ID == models.Video.channel_id)
        .filter(models.Video.video_id.in_(vids))
        .all()
    )

    videos = {
        v.video_id: {
            "id": v.video_id,
            "title": v.title,
            "thumbnail": v.thumbnail,
            "published_at": v.published_at,
            "channel": c.name,
        }
        for c, v in channel_videos
    }
    captions = defaultdict(list)
    for hit in hits["hits"]:
        captions[hit["_source"]["video_id"]].append(
            {
                "timestamp": hit["_source"]["start"] / 1000,
                "duration": hit["_source"]["duration"] / 1000,
                "caption": hit["_source"]["text"],
            }
        )
    for caption in captions.values():
        caption.sort(key=lambda x: x["timestamp"])

    if miss := (vids - set(videos.keys())):
        logger.warning(f"Missed videos: {miss}")

    return [
        {
            "info": videos[vid],
            "captions": captions[vid],
        }
        for vid in videos.keys()
    ]


# https://soudai-s.com/how-to-keep-the-diversity-of-search-results-in-elasticsearch
RANDOM_ORDER = {
    "sort": [
        {
            "_script": {
                "script": "Math.random() * 200000",
                "type": "number",
                "order": "asc",
            }
        }
    ],
}


def TOKENIZER_QUERY_BODY(term: str, *filters) -> dict:
    body = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "text": term,
                    }
                },
            },
        },
    }
    if _f := [f for f in filters if f]:
        body["query"]["bool"]["filter"] = _f
    return body


def NGRAM_QUERY_BODY(term: str, *filters) -> dict:
    body = {
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": term,
                        "fields": ["text.ngram"],
                        "type": "phrase",
                    }
                },
            },
        },
    }
    if _f := [f for f in filters if f]:
        body["query"]["bool"]["filter"] = _f
    return body


def query_fuzzy(db: Session, term: str, offset=0, random=False, vids=None, cids=None):
    es = ElasticDb()

    filter_vids = list(vids) if vids else []
    if cids:
        query = (
            db.query(models.Video.video_id)
            .join(models.Channel, models.Channel.ID == models.Video.channel_id)
            .filter(models.Channel.cid.in_(cids))
            .with_entities(models.Video.video_id)
        )
        ch_vids = (x[0] for x in db.execute(query).fetchall())
        filter_vids += list(ch_vids)

    body = {
        # "sort": ["_score"],
        **TOKENIZER_QUERY_BODY(
            term,
            {
                "terms": {
                    "video_id.keyword": filter_vids,
                }
            }
            if filter_vids
            else {},
        ),
    }
    if random:
        body.update(RANDOM_ORDER)
    res = es.search(
        index="captions",
        body=body,
        from_=offset,
        size=53,
        # track_total_hits=not random,
    )

    hits = res["hits"]
    if hits == []:
        return {
            "summary": {
                "query": term,
                "curr_offset": 0,
                "next_offset": 0,
                "total_found": 0,
            },
            "items": [],
        }

    total_found = hits.get("total", {"value": -1})["value"]
    items = _sort_captions_by_video(db, hits)

    return {
        "summary": {
            "query": term,
            "curr_offset": offset,
            "next_offset": offset + 53,
            "total_found": total_found,
        },
        "items": items,
    }


def query_fuzzy_intense(db: Session, term: str, vids=None, cids=None):
    es = ElasticDb()

    res = es.search(
        index="captions",
        body={
            # "sort": ["_score"],
            **TOKENIZER_QUERY_BODY(
                term,
                {
                    "terms": {
                        "video_id.keyword": list(vids),
                    }
                }
                if vids
                else {},
            ),
            **RANDOM_ORDER,
        },
        size=47,
        # track_total_hits=False,
    )

    hits = res["hits"]
    if hits == []:
        return {
            "summary": {
                "query": term,
                "curr_offset": 0,
                "next_offset": 0,
                "total_found": 0,
            },
            "items": [],
        }

    vids = set(hit["_source"]["video_id"] for hit in hits["hits"])
    res = es.search(
        index="captions",
        body={
            **TOKENIZER_QUERY_BODY(
                term,
                {
                    "terms": {
                        "video_id.keyword": list(vids),
                    }
                },
            ),
        },
        size=400,
        # track_total_hits=False,
    )
    hits = res["hits"]
    total_found = hits.get("total", {"value": -1})["value"]
    items = _sort_captions_by_video(db, hits)

    return {
        "summary": {
            "query": term,
            "curr_offset": 0,
            "next_offset": 47,
            "total_found": total_found,
        },
        "items": items,
    }


def query_phrase(db: Session, term: str, offset=0, random=False, vids=None, cids=None):
    es = ElasticDb()

    body = {
        **NGRAM_QUERY_BODY(
            term,
            {
                "terms": {
                    "video_id.keyword": list(vids),
                }
            }
            if vids
            else {},
        ),
    }
    if random:
        body.update(RANDOM_ORDER)
    res = es.search(
        index="captions",
        body=body,
        size=53,
        from_=offset,
        # track_total_hits=not random,
    )

    hits = res["hits"]
    if hits == []:
        return {
            "summary": {
                "query": term,
                "curr_offset": 0,
                "next_offset": 0,
                "total_found": 0,
            },
            "items": [],
        }

    total_found = hits.get("total", {"value": -1})["value"]
    items = _sort_captions_by_video(db, hits)

    return {
        "summary": {
            "query": term,
            "curr_offset": offset,
            "next_offset": offset + 53,
            "total_found": total_found,
        },
        "items": items,
    }


def query_phrase_intense(db: Session, term: str, vids=None, cids=None):
    es = ElasticDb()

    res = es.search(
        index="captions",
        body={
            **NGRAM_QUERY_BODY(
                term,
                {
                    "terms": {
                        "video_id.keyword": list(vids),
                    }
                }
                if vids
                else {},
            ),
            **RANDOM_ORDER,
        },
        size=47,
        # track_total_hits=False,
    )

    hits = res["hits"]
    if hits == []:
        return {
            "summary": {
                "query": term,
                "curr_offset": 0,
                "next_offset": 0,
                "total_found": 0,
            },
            "items": [],
        }

    vids = set(hit["_source"]["video_id"] for hit in hits["hits"])
    res = es.search(
        index="captions",
        body={
            # "sort": ["_score"],
            **NGRAM_QUERY_BODY(
                term,
                {
                    "terms": {
                        "video_id.keyword": list(vids),
                    }
                },
            ),
        },
        size=400,
        # track_total_hits=False,
    )
    hits = res["hits"]
    total_found = hits.get("total", {"value": -1})["value"]
    items = _sort_captions_by_video(db, hits)

    return {
        "summary": {
            "query": term,
            "curr_offset": 0,
            "next_offset": 47,
            "total_found": total_found,
        },
        "items": items,
    }


def query_phrase_for_video(db: Session, vid: str):
    es = ElasticDb()

    import elasticsearch.helpers

    res = elasticsearch.helpers.scan(
        es,
        index="captions",
        # preserve_order=True,
        query={
            "query": {
                "match": {
                    "video_id": vid,
                },
            },
            # "sort": [
            #     "start"
            # ]
        },
    )

    hits = list(res)

    items = (
        [
            {
                "timestamp": hit["_source"]["start"] / 1000,
                "duration": hit["_source"]["duration"] / 1000,
                "caption": hit["_source"]["text"],
            }
            for hit in hits
        ]
        if hits
        else []
    )

    return {
        "summary": {
            "query": vid,
            "curr_offset": 0,
            "next_offset": len(items),
            "total_found": len(items),
        },
        "items": items,
    }
