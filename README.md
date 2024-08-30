# Kiitemiru

A local Japanese Youtube caption search engine site.

0. setup database

```bash
python3 setup_elasticdb.py
```

1. import caption data by Channel ID

```bash
python3 import_data.py --cid xxx
```

2. search any word or phrase you like

## Requirements

- Python >= 3.11
    - with SSL, or you can not pip anything
    - pip install -r requirements.txt
- Elasticsearch Engine
- Elasticsearch Plugin
    - analysis-icu
    - analysis-kuromoji
- MariaDB

## System

- RAM >= 4GB

## References

1. [はじめての Elasticsearch #Kibana - Qiita](https://qiita.com/nskydiving/items/1c2dc4e0b9c98d164329#インストール)
2. [How to implement Japanese full-text search in Elasticsearch | Elastic Blog](https://www.elastic.co/jp/blog/how-to-implement-japanese-full-text-search-in-elasticsearch)

