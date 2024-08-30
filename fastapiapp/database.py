import os
from dotenv import load_dotenv

from elasticsearch import Elasticsearch
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()
# https://medium.com/@iambkpl/setup-fastapi-and-sqlalchemy-mysql-986419dbffeb

# SQLALCHEMY_DATABASE_URL = "sqlite:///./data.db"
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}"
)
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False}
    # echo=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ElasticDb() -> Elasticsearch:
    if os.getenv("ELASTIC_USERNAME"):
        return Elasticsearch(
            os.getenv("ELASTIC_HOST"),
            basic_auth=(
                os.getenv("ELASTIC_USERNAME"),
                os.getenv("PASSWORD_ELASTIC"),
            ),
        )
    else:
        return Elasticsearch(os.getenv("ELASTIC_HOST"))
