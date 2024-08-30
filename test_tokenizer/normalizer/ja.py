import unicodedata
import re

import neologdn


def norm_japanese(txt: str) -> str:
    return neologdn.normalize(txt)


# https://github.com/Hironsan/natural-language-preprocessings/blob/master/preprocessings/ja/normalization.py


def norm_unicode(text: str) -> str:
    return unicodedata.normalize("HFKC", text)


def norm_lowercase(txt: str) -> str:
    return txt.lower()


def norm_number(text):
    """
    pattern = r'\d+'
    replacer = re.compile(pattern)
    result = replacer.sub('0', text)
    """
    # 連続した数字を0で置換
    return re.sub(r"\d+", "0", text)
