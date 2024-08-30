from dataclasses import dataclass
from typing import Iterable
from tokenizer.base import Tokenizer
from tokenizer.base import Token

from janome import tokenizer


@dataclass
class JanomeNode:
    surface: str
    reading: str
    phonetic: str
    base_form: str
    speeches: str
    infl_type: str
    infl_form: str


class tJanome(Tokenizer):
    def __init__(self):
        self.parser = tokenizer.Tokenizer()

    def parse(self, txt: str) -> Iterable[Token]:
        for token in self.parser.tokenize(txt):
            yield JanomeNode(
                surface=token.surface,
                reading=token.reading,
                phonetic=token.phonetic,
                base_form=token.base_form,
                speeches=token.part_of_speech,
                infl_type=token.infl_type,
                infl_form=token.infl_form,
            )
