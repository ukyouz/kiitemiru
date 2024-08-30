from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy import Index
from sqlalchemy.schema import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.mysql import LONGTEXT, BIGINT, TIMESTAMP
from sqlalchemy.sql import func

from fastapiapp.database import Base


class Channel(Base):
    __tablename__ = "channels"
    ID = Column(
        Integer,
        primary_key=True,
    )
    name = Column(String(255))
    cid = Column(String(24), unique=True, index=True)
    thumbnail = Column(String(2048))
    last_sync_date = Column(String(20))

    # videos = relationship("Video", back_populates="channel")


class Video(Base):
    __tablename__ = "videos"
    ID = Column(BIGINT(unsigned=True), primary_key=True)
    channel_id = Column(BIGINT(unsigned=True))
    video_id = Column(String(16), unique=True, index=True)
    title = Column(String(255))
    thumbnail = Column(String(2048))
    published_at = Column(String(20))
    duration = Column(BIGINT(unsigned=True))
    # channel = relationship("Channel", back_populates="videos")
    # captions = relationship("Caption", back_populates="video")


class User(Base):
    __tablename__ = "users"
    ID = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_nicename = Column(String(50))
    user_email = Column(String(100), unique=True, index=True)
    user_pass = Column(String(255))
    user_registered = Column(TIMESTAMP, server_default=func.now())
    user_activation_key = Column(String(255))


class UserMeta(Base):
    __tablename__ = "usermeta"
    umeta_id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(BIGINT(unsigned=True), index=True)
    meta_key = Column(String(255))
    meta_value = Column(LONGTEXT)

    __table_args__ = (Index("meta_key_id", "meta_key", mysql_length=191),)


class Post(Base):
    __tablename__ = "posts"
    ID = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    post_title = Column(Text)
    post_author = Column(BIGINT, default=0, index=True)
    post_content = Column(LONGTEXT)
    post_parent = Column(BIGINT, index=True)
    post_name = Column(String(200))
    post_type = Column(String(20), default="post")
    post_status = Column(String(20), default="publish")
    created_date = Column(TIMESTAMP, server_default=func.now())
    modified_date = Column(TIMESTAMP, onupdate=func.now())

    __table_args__ = (
        Index("post_name_idx", "post_name", mysql_length=191),
        Index("post_type_idx", "post_type", "post_status", "created_date", "ID"),
    )


class PostMeta(Base):
    __tablename__ = "postmeta"
    meta_id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    post_id = Column(BIGINT(unsigned=True), default=0, index=True)
    meta_key = Column(String(255))
    meta_value = Column(LONGTEXT)

    __table_args__ = (Index("meta_key_id", "meta_key", mysql_length=191),)


class Term(Base):
    __tablename__ = "terms"
    term_id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    name = Column(String(200))
    slug = Column(String(200))

    __table_args__ = (
        Index("name", "name", mysql_length=191),
        Index("slug", "slug", mysql_length=191),
    )


class TermRelationship(Base):
    __tablename__ = "term_relationships"
    object_id = Column(BIGINT(unsigned=True))
    term_taxonomy_id = Column(BIGINT(unsigned=True), index=True)
    term_order = Column(Integer)

    __table_args__ = (PrimaryKeyConstraint("object_id", "term_taxonomy_id"),)


class TermTaxonomy(Base):
    __tablename__ = "term_taxonomy"
    term_taxonomy_id = Column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    term_id = Column(BIGINT(unsigned=True), index=True)
    taxonomy = Column(String(32))
    description = Column(LONGTEXT)
    parent = Column(BIGINT(unsigned=True))
    count = Column(BIGINT)

    __table_args__ = (
        Index("term_id_taxonomy_id", "term_id", "taxonomy"),
        Index("taxonomy_id", "taxonomy"),
        UniqueConstraint("term_id", "taxonomy"),
    )
