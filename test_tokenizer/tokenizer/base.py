from typing import Protocol
from typing import Iterable


class Token(Protocol):
    surface: str  # 表層形
    speeches: str  # 品詞
    infl_type: str  # 活用型
    infl_form: str  # 活用形
    base_form: str  # 基本形、見出し語
    reading: str  # 読み
    phonetic: str  # 発音


class Tokenizer:
    def parse(self, txt: str) -> Iterable[Token]:
        ...


