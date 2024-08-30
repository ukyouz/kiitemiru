import sqlite3
import logging
from typing import Any, Protocol, Self, Type

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DataclassType(Protocol):
    __annotations__: dict[str, Any] = {}
    __dataclass_fields__: dict = {}


class UniqueStr(str): ...


class Sqlite:
    typemap = {
        str: "{} TEXT",
        int: "{} INTEGER",
        UniqueStr: "{} TEXT UNIQUE",
    }

    def __init__(self, dbfile: str) -> None:
        self._dbfile = dbfile

    def __enter__(self) -> Self:
        self.con = sqlite3.connect(self._dbfile)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, *a):
        self.con.close()

    def drop_table(self, t: Type[DataclassType]):
        try:
            self.cur.execute("DROP TABLE  {}".format(t.__name__))
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e):
                raise e

    def create_table(self, t: Type[DataclassType], exists_ok=False):
        fields = [(k, v) for k, v in t.__annotations__.items() if not k.startswith("__")]
        args = [
            self.typemap.get(typ, "%s text").format(
                attr, getattr(t, attr, "")
            )
            for attr, typ in fields
        ]
        args += [
            "UNIQUE({})".format(", ".join(getattr(t, "__constrains__", [])))
        ]
        args += [
            "FOREIGN KEY ({}) REFERENCES {}".format(*foreign)
            for foreign in getattr(t, "__foreigns__", [])
        ]
        sql = "CREATE TABLE {}({})".format(
            t.__name__,
            ", ".join(args),
        )
        logger.debug(sql)
        try:
            self.cur.execute(sql)
        except sqlite3.OperationalError as e:
            if ("table %s already exists" % t.__name__) in str(e) and exists_ok:
                ...
            else:
                raise e

    def create_table_with_fts(self, t: Type[DataclassType], exists_ok=False):
        fields = [(k, v) for k, v in t.__annotations__.items() if not k.startswith("__")]
        args = [attr for attr, _ in fields ]
        sql = "CREATE VIRTUAL TABLE {} USING fts5({})".format(
            t.__name__,
            ", ".join(args),
        )
        logger.debug(sql)
        try:
            self.cur.execute(sql)
        except sqlite3.OperationalError as e:
            if ("table %s already exists" % t.__name__) in str(e) and exists_ok:
                ...
            else:
                raise e

    def select_lastid(self, t: Type[DataclassType]) -> int:
        rows = list(self.iter_rows(t, "MAX(rowid)", "LIMIT 1"))
        if rows == []:
            return 0
        else:
            return rows[0][0] or 0

    def insert_rows(self, t: Type[DataclassType], fields: list[DataclassType]) -> list[int]:
        if fields == []:
            return []
        prev_id = self.select_lastid(t)
        _t = type(fields[0])
        keys = [f for f, t in _t.__annotations__.items() if not f.startswith("__")]
        self.cur.execute(
            "INSERT INTO {} {} VALUES {};".format(
                t.__name__,
                "(%s)" % ",".join(f for f in keys),
                ",".join(
                    "(%s)" % ",".join(repr(getattr(x, k)) for k in keys) for x in fields
                ),
            )
        )
        self.con.commit()
        ids = list(range(prev_id + 1, self.select_lastid(t) + 1))
        return ids

    def insert_row(self, field: DataclassType, exists_ok=False) -> int:
        _typ = field.__class__
        keys = [f for f, t in field.__annotations__.items() if not f.startswith("__")]
        cond = " AND ".join("%s = %r" % (k, getattr(field, k)) for k in getattr(field, "__constrains__", keys))
        try:
            ids = self.insert_rows(_typ, [field])
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                if not exists_ok:
                    raise e
                ids = [x[0] for x in self.iter_rows(_typ, "rowid", "WHERE " + cond)]
            else:
                raise e
        if ids == []:
            assert False, "Table %r WHERE %s" % (_typ.__name__, cond)
        return ids[0]

    def iter_rows(self, t: Type[DataclassType], fields: str, cond: str = ""):
        self.cur.execute(
            "SELECT {} from {} {};".format(
                fields,
                t.__name__,
                cond,
            )
        )
        for row in self.cur.fetchall():
            idx, attrs = row[0], row[1:]
            yield idx, attrs
