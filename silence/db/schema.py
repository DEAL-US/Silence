import threading

from silence.db import dal
from silence.settings import settings

###############################################################################
# Introspection of the database schema: tables, views, columns, keys.
# The result is cached until invalidate() is called (e.g., by the admin
# panel before generating endpoints).
###############################################################################

_cache = None
_lock = threading.Lock()


class Column:
    def __init__(self, row):
        self.name = row["COLUMN_NAME"]
        self.data_type = row["DATA_TYPE"].lower()
        self.column_type = row["COLUMN_TYPE"]
        self.nullable = row["IS_NULLABLE"] == "YES"
        # MariaDB returns the string 'NULL' for "DEFAULT NULL" and NULL for no default
        self.has_default = row["COLUMN_DEFAULT"] is not None
        self.default = row["COLUMN_DEFAULT"]
        extra = (row["EXTRA"] or "").lower()
        self.auto_increment = "auto_increment" in extra
        self.generated = "generated" in extra
        self.max_length = row["CHARACTER_MAXIMUM_LENGTH"]

    @property
    def optional(self):
        '''Whether an INSERT can leave this column out'''
        return self.nullable or self.has_default or self.auto_increment or self.generated

    def to_dict(self):
        return {
            "name": self.name, "type": self.column_type, "nullable": self.nullable,
            "default": self.default, "autoIncrement": self.auto_increment,
            "generated": self.generated, "optional": self.optional,
        }


class Relation:
    '''A table or a view'''
    def __init__(self, name, is_view):
        self.name = name
        self.is_view = is_view
        self.columns = {}       # name -> Column, in order
        self.pk = []            # column names
        self.fks = []           # {"column", "refTable", "refColumn"}
        self.uniques = []       # lists of column names (UNIQUE indexes)

    def column(self, name):
        '''Case-insensitive lookup of a column'''
        if name in self.columns:
            return self.columns[name]
        return next((c for n, c in self.columns.items() if n.lower() == name.lower()), None)

    @property
    def single_pk(self):
        return self.pk[0] if len(self.pk) == 1 else None

    def unique_columns(self):
        '''Columns that must be unique on their own (single-column UNIQUE or PK)'''
        res = {u[0] for u in self.uniques if len(u) == 1}
        if len(self.pk) == 1:
            res.add(self.pk[0])
        return res

    def to_dict(self):
        return {
            "name": self.name, "view": self.is_view, "pk": self.pk, "fks": self.fks,
            "uniques": self.uniques, "columns": [c.to_dict() for c in self.columns.values()],
        }


class Schema:
    def __init__(self):
        self.relations = {}

    @property
    def tables(self):
        return {n: r for n, r in self.relations.items() if not r.is_view}

    def get(self, name):
        '''Case-insensitive lookup of a table or view'''
        if name in self.relations:
            return self.relations[name]
        return next((r for n, r in self.relations.items() if n.lower() == name.lower()), None)

    def referencing(self, table_name):
        '''FKs of other tables that reference the given one: [(table, fk)]'''
        return [(t, fk) for t in self.tables.values() for fk in t.fks
                if fk["refTable"].lower() == table_name.lower()]

    def to_dict(self):
        return {"database": settings.DB_CONN["database"],
                "relations": [r.to_dict() for r in self.relations.values()]}


def load_schema():
    db = settings.DB_CONN["database"]
    schema = Schema()

    for row in dal.query(
            "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME", (db,)):
        name = row["TABLE_NAME"]
        schema.relations[name] = Relation(name, row["TABLE_TYPE"] == "VIEW")

    for row in dal.query(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, "
            "COLUMN_DEFAULT, EXTRA, CHARACTER_MAXIMUM_LENGTH, ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,)):
        rel = schema.relations.get(row["TABLE_NAME"])
        if rel:
            rel.columns[row["COLUMN_NAME"]] = Column(row)

    indexes = {}
    for row in dal.query(
            "SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE FROM INFORMATION_SCHEMA.STATISTICS "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX", (db,)):
        if int(row["NON_UNIQUE"]) == 0:
            indexes.setdefault((row["TABLE_NAME"], row["INDEX_NAME"]), []).append(row["COLUMN_NAME"])
    for (table, index), cols in indexes.items():
        rel = schema.relations.get(table)
        if not rel:
            continue
        if index == "PRIMARY":
            rel.pk = cols
        else:
            rel.uniques.append(cols)

    for row in dal.query(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = %s "
            "AND REFERENCED_TABLE_NAME IS NOT NULL", (db,)):
        rel = schema.relations.get(row["TABLE_NAME"])
        if rel:
            rel.fks.append({"column": row["COLUMN_NAME"], "refTable": row["REFERENCED_TABLE_NAME"],
                            "refColumn": row["REFERENCED_COLUMN_NAME"]})

    return schema


def get_schema(refresh=False):
    global _cache
    with _lock:
        if _cache is None or refresh:
            _cache = load_schema()
        return _cache


def invalidate():
    global _cache
    with _lock:
        _cache = None
