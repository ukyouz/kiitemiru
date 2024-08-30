import os
from dotenv import load_dotenv
from pprint import pprint

from elasticsearch import Elasticsearch

load_dotenv()

es = Elasticsearch(
    os.getenv("ELASTIC_HOST"),
    basic_auth=(
        os.getenv("ELASTIC_USERNAME"),
        os.getenv("PASSWORD_ELASTIC"),
    ),
)

# fmt: off
config = {
    "settings": {
        # "number_of_shards": 1,
        # "number_of_replicas": 1,
        "analysis": {
            "char_filter": {
                "my_char_filter": {
                    "type": "icu_normalizer",
                    "name": "nfkc",
                    "mode": "compose",
                }
            },
            "tokenizer": {
                "ja_kuromoji_tokenizer": {
                    "mode": "search",
                    "type": "kuromoji_tokenizer",
                    "discard_compound_token": True,  # 複合語出力なし
                    "user_dictionary_rules": [],
                },
                "ja_ngram_tokenizer": {
                    "type": "ngram",
                    "min_gram": 2,
                    "max_gram": 3,
                    "token_chars": ["letter", "digit"],
                },
            },
            # user_dictionary_rules、synonyms
            "analyzer": {
                "kuromoji_analyzer": {
                    "type": "custom",
                    "tokenizer": "ja_kuromoji_tokenizer",
                    # tokenizer: 'kuromoji_tokenizer',
                    "filter": [
                        "kuromoji_baseform",

                        # 寿司がおいしいね → 「寿司」「おいしい」だけ残し、「が」と「ね」を消す
                        # "kuromoji_part_of_speech",

                        "cjk_width",  # 文字幅正規

                        "ja_stop",
                        # 長音「ー」排除 プリンター → プリンタのように長音を削除（※minimumlengthなどの設定ができる。)
                        # https://www.elastic.co/guide/en/elasticsearch/plugins/current/analysis-kuromoji-stemmer.html）
                        "kuromoji_stemmer",

                        # "lowercase",

                        # 一〇〇〇（漢数字のゼロ）→1000にする（※反応しない）
                        'kuromoji_number',
                    ],
                    # 半角・全角（㌀ → アパート）
                    "char_filter": [
                        "icu_normalizer",  # 文字の正規化
                        "html_strip",  # html排除
                        "my_char_filter",
                    ],
                },
                "ja_ngram_analyzer": {
                    "type": "custom",
                    "char_filter": [
                        "icu_normalizer",  # 文字の正規化
                        "html_strip",  # html排除
                        "my_char_filter",
                    ],
                    "tokenizer": "ja_ngram_tokenizer",
                    "filter": ["lowercase"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "duration" : {
                "type" : "integer"
            },
            "start" : {
                "type" : "integer"
            },
            "text": {
                "type": "text",
                "analyzer": "kuromoji_analyzer",
                "fields": {
                    "ngram": {
                        "type": "text",
                        "analyzer": "ja_ngram_analyzer",
                    },
                },
            },
            "video_id" : {
                "type" : "text",
                "fields" : {
                    "keyword" : {
                        "type" : "keyword",
                        "ignore_above" : 256
                    }
                }
            }
        }
    },
}
# fmt: on


def search(term):
    print("== {} ==============".format(term))
    res = es.search(
        index="captions",
        body={
            "sort": ["_score"],
            "query": {
                "match": {"text": term},
            },
        },
    )
    if res["hits"] == []:
        pprint([h["_source"]["text"] for h in res["hits"]["hits"]], width=40)
    else:
        print("[]")
    print("-----")
    res = es.search(
        index="captions",
        body={
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": term,
                                "fields": ["text.ngram"],
                                "type": "phrase",
                            }
                        }
                    ]
                }
            }
        },
    )
    if res["hits"]:
        pprint([h["_source"]["text"] for h in res["hits"]["hits"]], width=40)
    else:
        print("[]")


es.indices.delete(index="captions", ignore=404)
es.indices.create(
    index="captions",
    # ignore=400,
    body=config,
)
