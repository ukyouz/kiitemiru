from dataclasses import dataclass
from typing import Iterable
from tokenizer.base import Tokenizer
import MeCab

@dataclass
class MeCabNode:
    surface: str
    speeches: str
    infl_type: str
    infl_form: str
    base_form: str
    reading: str
    phonetic: str


class tMeCab(Tokenizer):
    def __init__(self):
        self.tagger = MeCab.Tagger("-r /dev/null -d /opt/homebrew/lib/mecab/dic/mecab-ipadic-neologd")

    def parse(self, txt: str) -> list[MeCabNode]:
        res = self.tagger.parse(txt)

        nodes = []
        for token in res.split("\n"):
            if token == "EOS":
                break
            surface, feature = token.split("\t")
            features = feature.split(",")
            speech = ",".join(features[:4])
            rest = features[4:]
            if len(rest) != 5:
                continue
            nodes.append(MeCabNode(surface, speech, *rest))

        return nodes



