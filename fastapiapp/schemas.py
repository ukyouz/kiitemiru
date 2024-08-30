from pydantic import BaseModel


class ChannelBase(BaseModel):
    name: str
    cid: str
    thumbnail: str
    last_sync_date: str


class ChannelCreate(ChannelBase):
    pass


class Channel(ChannelBase):
    rowid: int

    class Config:
        orm_mode = True


class VideoBase(BaseModel):
    channel_id: int
    video_id: str
    title: str
    thumbnail: str
    published_dt: str


class VideoCreate(VideoBase):
    pass


class Video(VideoBase):
    rowid: int

    class Config:
        orm_mode = True
