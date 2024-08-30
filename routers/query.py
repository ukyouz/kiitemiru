import re

from typing import Annotated
from fastapi import Request
from fastapi import APIRouter
from fastapi import Depends
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.orm import Session
from dependencies import get_db
import crud

router = APIRouter(
    prefix="/query",
    dependencies=[Depends(get_db)],
)


DbType = Annotated[Session, Depends(get_db)]


YT_VID_REGEX = re.compile(r"#[0-9A-Za-z_-]{10}[048AEIMQUYcgkosw]")
YT_CH_REGEX = re.compile(r"#UC[0-9A-Za-z_-]{21}[AQgw]")


def query_params(q: str = "", offset: int = 0, options: str = ""):
    opts = options.split("|")
    videos = YT_VID_REGEX.findall(q)
    channelds = YT_CH_REGEX.findall(q)
    for kw in videos + channelds:
        q = q.replace(kw, "")
    return {
        "q": q.strip(),
        "offset": offset,
        "is_random": "random" in opts,
        "is_intense": "intense" in opts,
        "is_fuzzy": "ngram" not in opts,
        "videos": [x[1:] for x in videos],
        "channels": [x[1:] for x in channelds],
    }


QType = Annotated[str, Depends(query_params)]


@router.get("/search")
async def query_captions(request: Request, q: QType, db: DbType):
    # await csrf_protect.validate_csrf(request)
    term = q["q"]
    videos = q.get("videos", [])
    channels = q.get("channels", [])
    if q["is_fuzzy"]:
        if q["is_intense"]:
            return crud.query_fuzzy_intense(
                db,
                term,
                vids=videos,
                cids=channels,
            )
        else:
            return crud.query_fuzzy(
                db,
                term,
                offset=q["offset"],
                random=q["is_random"],
                vids=videos,
                cids=channels,
            )
    else:
        if q["is_intense"]:
            return crud.query_phrase_intense(
                db,
                term,
                vids=videos,
                cids=channels,
            )
        else:
            return crud.query_phrase(
                db,
                term,
                offset=q["offset"],
                random=q["is_random"],
                vids=videos,
                cids=channels,
            )


# @router.get("/fuzzy/{term}/random")
# def query_fuzzy_random(term: str, q: QType, db: DbType):
#     return crud.query_fuzzy(db, term, random=True)


# @router.get("/phrase/{term}/{offset}")
# def query_phrase(term: str, offset: int, q: QType, db: DbType):
#     return crud.query_phrase(db, term, offset=offset)


# @router.get("/fuzzy/{term}/{offset}")
# def query_fuzzy(term: str, offset: int, q: QType, db: DbType):
#     return crud.query_fuzzy(db, term, offset=offset)


# @router.get("/phrase/{term}")
# def query_phrase_intense(term: str, q: QType, db: DbType):
#     return crud.query_phrase_intense(db, term)


# @router.get("/fuzzy/{term}")
# def query_fuzzy_intense(term: str, q: QType, db: DbType):
#     return crud.query_fuzzy_intense(db, term)
