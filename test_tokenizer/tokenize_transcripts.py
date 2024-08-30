import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass

from db.sqlite3 import Sqlite

from tokenizer import mecab, jnm


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class Caption:
    video_id: str
    time_ms: int
    line: str
    __constrains__ = ("video_id", "time_ms")


@dataclass
class CaptionMeta:
    caption_id: int
    duration_ms: int
    __constrains__ = ("caption_id", "time_ms")
    __foreigns__ = (
        ("caption_id", "Caption(rowid)"),
    )


@dataclass
class WordForm:
    word_id: int
    infl_form: str
    surface: str
    reading: str
    __constrains__ = ("surface", "infl_form", "word_id")
    __foreigns__ = (
        ("word_id", "Word(rowid)"),
    )


@dataclass
class Word:
    baseterm: str
    infl_type: str
    speech: str
    __constrains__ = ("baseterm", "infl_type", "speech")


@dataclass
class Token:
    caption_id: int
    wordform_id: int
    __constrains__ = ("caption_id", "wordform_id")
    __foreigns__ = (
        ("caption_id", "Caption(rowid)"),
        ("wordform_id", "WordForm(rowid)"),
    )


def load_phrases(video_file: Path) -> tuple[list[Caption], list[CaptionMeta]]:
    from youtube.transcript import CaptionData

    # TODO: change to use api
    with open(video_file) as fs:
        data: list[CaptionData] = json.load(fs)

    captions = [
        Caption(
            video_file.stem,
            c["text"],
        )
        for c in data
    ]
    phrasemetas = [
        CaptionMeta(
            -1,
            int(c["start"] * 1000),
            int(c["duration"] * 1000),
        )
        for c in data
    ]
    return captions, phrasemetas


def init_database(dbfile: str):
    with Sqlite(dbfile) as db:
        db.drop_table(Caption)
        db.create_table_with_fts(Caption, exists_ok=True)
        db.drop_table(CaptionMeta)
        db.create_table(CaptionMeta, exists_ok=True)
        db.drop_table(Token)
        db.create_table(Token, exists_ok=True)
        db.drop_table(WordForm)
        db.create_table(WordForm, exists_ok=True)
        db.drop_table(Word)
        db.create_table(Word, exists_ok=True)


def store_captions(dbfile: str, captions: list[Caption], metas: list[CaptionMeta]):
    tm = mecab.tMeCab()
    # tm = jnm.tJanome()
    with Sqlite(dbfile) as db:
        for c, m in zip(captions, metas):
            tokens = list(tm.parse(c.line))
            c.line = " ".join(t.surface for t in tokens)
            try:
                pid = db.insert_row(c)
            except sqlite3.IntegrityError:
                continue
            m.caption_id = pid
            db.insert_row(m)
            # tokens = list(tz.tokenize(p.line))
            for t in tokens:
                if t.reading == "*":
                    continue
                wid = db.insert_row(Word(t.base_form, t.infl_type, t.speeches), exists_ok=True)
                form_id = db.insert_row(
                    WordForm(wid, t.infl_form, t.surface, t.reading), exists_ok=True
                )
                db.insert_row(Token(pid, form_id), exists_ok=True)


def main(caption_file: Path):
    captions, metas = load_phrases(caption_file)
    store_captions("data.db", captions, metas)


if __name__ == "__main__":
    caption_folder = Path("youtube/data/captions")
    # init_database("data.db")
    for caption_file in list(caption_folder.glob("*.json")):
        logger.info("Processing %s", caption_file)
        main(caption_file)
