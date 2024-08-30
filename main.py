import logging
from datetime import datetime
from typing import Union

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from jinja_markdown import MarkdownExtension
from pydantic import BaseModel
from sqlalchemy.orm import Session

import crud
from fastapiapp import models
from fastapiapp import schemas
from fastapiapp.database import engine
from routers import query
from dependencies import get_db

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s - %(message)r %(asctime)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


app = FastAPI()
origins = [
    "http://kiitemiru.com",
    "https://kiitemiru.com",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(directory="fastapiapp/templates")
templates.env.add_extension(MarkdownExtension)
app.mount("/static", StaticFiles(directory="fastapiapp/static"), name="static")
app.include_router(query.router)


def format_datetime(ts: str):
    # ts == "2024-04-23T09:45:01Z"
    # output to "2024-04-23 09:45:01"
    if ts:
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return ""


templates.env.globals["format_datetime"] = format_datetime


class CsrfSettings(BaseModel):
    secret_key: str = "asecrettoeverybody"
    cookie_samesite: str = "strict"


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


@app.get("/")
def read_root(request: Request, q: str = "", csrf_protect: CsrfProtect = Depends()):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    response = templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "id": 123,
            "title": q,
            "csrf_token": csrf_token,
        },
    )

    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@app.get("/database")
def read_db_channel(
    request: Request, db: Session = Depends(get_db), response_class=HTMLResponse
):
    info = crud.get_channels(db)

    return templates.TemplateResponse(
        request=request,
        name="database.html",
        context={
            "title": "Database",
            "total_duration": info["summary"]["total_duration"],
            "channels": info["items"],
        },
    )


@app.get("/database/{channel_id}")
def read_db_videos(
    channel_id: str,
    request: Request,
    db: Session = Depends(get_db),
    response_class=HTMLResponse,
):
    info = crud.get_videos(db, channel_id)
    return templates.TemplateResponse(
        request=request,
        name="database_channel.html",
        context={
            "title": info["name"],
            "channel": info,
        },
    )


@app.get("/page/{page_slug}")
def read_plain_html(page_slug: str, request: Request, response_class=HTMLResponse):
    return templates.TemplateResponse(
        request=request,
        name=f"{page_slug}.html",
        context={
            "title": page_slug.title(),
        },
    )


# @app.get("/channels")
# def read_channels(db: Session = Depends(get_db)):
#     db_channel = crud.get_channels(db)
#     if db_channel is None:
#         raise HTTPException(status_code=404, detail="Channel not found")
#     return db_channel


@app.get("/channel/{channel_id}", response_model=schemas.Channel)
def read_channel(cid: str, db: Session = Depends(get_db)):
    db_channel = crud.get_channel(db, channel_id=cid)
    if db_channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return db_channel


@app.get("/query-video/captions/{vid}")
def query_video_captions(vid: str, db: Session = Depends(get_db)):
    return crud.query_phrase_for_video(db, vid)


# 404エラーを拾う
@app.exception_handler(404)
def not_found(req: Request, exc: HTTPException) -> HTMLResponse:
    return templates.TemplateResponse(
        request=req,
        name="404.html",
        context={},
    )


@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
