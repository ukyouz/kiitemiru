# Kiitemiru

A local Japanese Youtube caption search engine site.

## Requirements

- Python >= 3.11
    - with SSL, or you can not pip anything
    - pip install -r requirements.txt
- Elasticsearch Engine
- Elasticsearch Plugin
    - analysis-icu
    - analysis-kuromoji
- MariaDB

## Setup

0. add .env file

Add `.env` file to setup environment.
```ini
ELASTIC_HOST=http://localhost:9200
ELASTIC_USERNAME=elasticsearch
PASSWORD_ELASTIC=

MYSQL_HOST=localhost/<dbname>
MYSQL_USERNAME=xxx
MYSQL_PASSWORD=xxxxxxxxxx

YT_API_KEY=KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK
```

1. setup db

```bash
python3 setup_elasticdb.py
```

2. import caption data by Channel ID

```bash
python3 import_data.py xxxxxxxxxxxxxxxxxxxxxxxx
```

3. search any word or phrase you like

start web server.

```bash
python3 main.py
```

## System

- RAM >= 4GB

## References

1. [はじめての Elasticsearch #Kibana - Qiita](https://qiita.com/nskydiving/items/1c2dc4e0b9c98d164329#インストール)
2. [How to implement Japanese full-text search in Elasticsearch | Elastic Blog](https://www.elastic.co/jp/blog/how-to-implement-japanese-full-text-search-in-elasticsearch)

