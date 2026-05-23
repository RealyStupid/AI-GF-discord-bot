import sqlcipher3
from typing import Iterable

#  COLUMN BUILDER
class _ColumnBuilder:
    def __init__(self, name: str):
        self.name = name
        self.type = None
        self.constraints = []
        self._type_set = False

    def __repr__(self):
        return f"<ColumnBuilder {self.to_sql()}>"

    # datatypes
    def int(self):
        self._set_type("INTEGER")
        return self

    def text(self):
        self._set_type("TEXT")
        return self

    def real(self):
        self._set_type("REAL")
        return self

    def blob(self):
        self._set_type("BLOB")
        return self

    def numeric(self):
        self._set_type("NUMERIC")
        return self

    # aliases
    def boolean(self): return self.numeric()
    def float(self): return self.real()
    def double(self): return self.real()
    def date(self): return self.text()
    def datetime(self): return self.text()

    def _set_type(self, t):
        if self._type_set:
            raise ValueError("Type already set for this column")
        self.type = t
        self._type_set = True

    # constraints
    def primary_key(self):
        self._require_type()
        self._add_constraint("PRIMARY KEY")
        return self

    def not_null(self):
        self._require_type()
        self._add_constraint("NOT NULL")
        return self

    def unique(self):
        self._add_constraint("UNIQUE")
        return self

    def default(self, value):
        if isinstance(value, str):
            value = f"'{value}'"
        self.constraints.append(f"DEFAULT {value}")
        return self

    def check(self, expression: str):
        self.constraints.append(f"CHECK ({expression})")
        return self

    def collate(self, collation: str):
        self.constraints.append(f"COLLATE {collation}")
        return self

    def autoincrement(self):
        if self.type != "INTEGER":
            raise ValueError("AUTOINCREMENT requires INTEGER type")
        if "PRIMARY KEY" not in self.constraints:
            raise ValueError("AUTOINCREMENT requires PRIMARY KEY")
        self.constraints.append("AUTOINCREMENT")
        return self

    def foreign_key(self, reference: str):
        self.constraints.append(f"REFERENCES {reference}")
        return self

    def on_conflict(self, rule: str):
        rule = rule.upper()
        if rule not in ("ROLLBACK", "ABORT", "FAIL", "IGNORE", "REPLACE"):
            raise ValueError("Invalid ON CONFLICT rule")
        self.constraints.append(f"ON CONFLICT {rule}")
        return self

    def _require_type(self):
        if not self._type_set:
            raise ValueError("Set a type before adding constraints")

    def _add_constraint(self, c):
        if c in self.constraints:
            raise ValueError(f"{c} already applied")
        self.constraints.append(c)

    def to_sql(self):
        if not self._type_set:
            raise ValueError("Column type not set")
        return " ".join([self.name, self.type] + self.constraints)

#  QUERY BUILDER
class _QueryBuilder:
    def __init__(self, table: str):
        self.table = table

        self._mode = None

        # SELECT state
        self._select_cols = []
        self._joins = []          # (type, table, left_col, right_col)
        self._where = []          # (condition_sql, params)
        self._group_by = []
        self._having = []         # (condition_sql, params)
        self._order_by = None
        self._limit = None
        self._offset = None

        # INSERT state
        self._insert_cols = []
        self._insert_vals = []

        # UPDATE state
        self._update_pairs = {}

        # PARAMETER STORAGE
        self._params = []

    # -----------------------------
    # SELECT
    # -----------------------------
    def select(self, *cols):
        self._mode = "SELECT"
        self._select_cols.extend(cols)
        return self

    def join(self, table: str, left_col: str, right_col: str):
        self._joins.append(("JOIN", table, left_col, right_col))
        return self

    def left_join(self, table: str, left_col: str, right_col: str):
        self._joins.append(("LEFT JOIN", table, left_col, right_col))
        return self

    def where(self, condition: str, *params):
        if "?" not in condition:
            raise ValueError("Strict mode: WHERE requires placeholders (e.g., 'age > ?').")
        self._where.append((condition, params))
        return self

    def group_by(self, *cols):
        self._group_by.extend(cols)
        return self

    def having(self, condition: str, *params):
        if "?" not in condition:
            raise ValueError("Strict mode: HAVING requires placeholders.")
        self._having.append((condition, params))
        return self

    def order_by(self, col: str, direction="ASC"):
        direction = direction.upper()
        if direction not in ("ASC", "DESC"):
            raise ValueError("order_by direction must be ASC or DESC")
        self._order_by = f"{col} {direction}"
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    def offset(self, n: int):
        self._offset = n
        return self

    # -----------------------------
    # INSERT
    # -----------------------------
    def insert(self, **kwargs):
        self._mode = "INSERT"
        for col, val in kwargs.items():
            self._insert_cols.append(col)
            self._insert_vals.append("?")
            self._params.append(val)
        return self

    # -----------------------------
    # UPDATE
    # -----------------------------
    def update(self, **kwargs):
        self._mode = "UPDATE"
        for col, val in kwargs.items():
            self._update_pairs[col] = "?"
            self._params.append(val)
        return self

    # -----------------------------
    # DELETE
    # -----------------------------
    def delete(self):
        self._mode = "DELETE"
        return self

    # -----------------------------
    # SQL BUILDERS
    # -----------------------------
    def to_sql(self):
        if self._mode == "SELECT":
            return self._build_select(), self._params
        if self._mode == "INSERT":
            return self._build_insert(), self._params
        if self._mode == "UPDATE":
            return self._build_update(), self._params
        if self._mode == "DELETE":
            return self._build_delete(), self._params
        raise ValueError("No query mode selected")

    def _build_select(self):
        sql = f"SELECT {', '.join(self._select_cols) if self._select_cols else '*'} FROM {self.table}"

        # JOINS
        for join_type, table, left, right in self._joins:
            sql += f" {join_type} {table} ON {left} = {right}"

        # WHERE
        if self._where:
            parts = []
            for cond, params in self._where:
                parts.append(cond)
                self._params.extend(params)
            sql += " WHERE " + " AND ".join(parts)

        # GROUP BY
        if self._group_by:
            sql += " GROUP BY " + ", ".join(self._group_by)

        # HAVING
        if self._having:
            parts = []
            for cond, params in self._having:
                parts.append(cond)
                self._params.extend(params)
            sql += " HAVING " + " AND ".join(parts)

        # ORDER BY
        if self._order_by:
            sql += f" ORDER BY {self._order_by}"

        # LIMIT / OFFSET
        if self._limit is not None:
            sql += " LIMIT ?"
            self._params.append(self._limit)

        if self._offset is not None:
            sql += " OFFSET ?"
            self._params.append(self._offset)

        return sql + ";"

    def _build_insert(self):
        cols = ", ".join(self._insert_cols)
        placeholders = ", ".join(self._insert_vals)
        return f"INSERT INTO {self.table} ({cols}) VALUES ({placeholders});"

    def _build_update(self):
        assignments = ", ".join([f"{col} = ?" for col in self._update_pairs])
        sql = f"UPDATE {self.table} SET {assignments}"

        if self._where:
            parts = []
            for cond, params in self._where:
                parts.append(cond)
                self._params.extend(params)
            sql += " WHERE " + " AND ".join(parts)

        return sql + ";"

    def _build_delete(self):
        sql = f"DELETE FROM {self.table}"

        if self._where:
            parts = []
            for cond, params in self._where:
                parts.append(cond)
                self._params.extend(params)
            sql += " WHERE " + " AND ".join(parts)

        return sql + ";"


#  PUBLIC FACTORY FUNCTIONS
def column(name: str) -> _ColumnBuilder:
    return _ColumnBuilder(name)

def query(table: str) -> _QueryBuilder:
    return _QueryBuilder(table)


# ============================================================
#  DATABASE MANAGER
# ============================================================

class db_manager:
    def __init__(self, directory: str, db_name: str, table_name: str, schema: Iterable):
        self.table_name = table_name
        self.directory = directory
        self.db_name = db_name

        # Store schema objects
        self.schema_objects = list(schema)

        # Extract column names dynamically
        self.columns = [col.name for col in self.schema_objects]

        self.schema = ", ".join(col.to_sql() for col in self.schema_objects)

        self._encryption_key = None

        print("Database Initialized with:")
        print(f"Name: {db_name}.db")
        print(f"Directory: {directory}")
        print(f"Table Name: {table_name}")
        print(f"Schema: {self.schema}")

    # INTERNAL CONNECTION HANDLER
    def _connect(self):
        _os = __import__("os")
        _os.makedirs(self.directory, exist_ok=True)

        path = f"{self.directory}/{self.db_name}.db"
        conn = sqlcipher3.connect(path)

        if self._encryption_key is not None:
            conn.execute(f"PRAGMA key = '{self._encryption_key}';")

            try:
                conn.execute("PRAGMA cipher_page_size = 4096;")
                conn.execute("PRAGMA kdf_iter = 256000;")
                conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512;")
                conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;")
                conn.execute("PRAGMA cipher_compatibility = 4;")
            except Exception:
                pass

            try:
                conn.execute("PRAGMA cipher_migrate;")
            except Exception:
                pass

        return conn

    # PRETTY PRINT ANY TABLE
    def print_table(self, table_name: str):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(f"PRAGMA table_info({table_name});")
        info = cur.fetchall()
        if not info:
            print(f"[ERROR] Table '{table_name}' does not exist.")
            conn.close()
            return

        columns = [col[1] for col in info]

        cur.execute(f"SELECT * FROM {table_name};")
        rows = cur.fetchall()
        conn.close()

        str_rows = [[str(item) for item in row] for row in rows]

        col_widths = []
        for i in range(len(columns)):
            if str_rows:
                width = max(len(columns[i]), *(len(r[i]) for r in str_rows))
            else:
                width = len(columns[i])
            col_widths.append(width)

        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        print("\n" + table_name)
        print(sep)

        header = "|" + "|".join(f" {columns[i].ljust(col_widths[i])} " for i in range(len(columns))) + "|"
        print(header)
        print(sep)

        for row in str_rows:
            line = "|" + "|".join(f" {row[i].ljust(col_widths[i])} " for i in range(len(row))) + "|"
            print(line)

        print(sep)
        print(f"{len(rows)} row(s).\n")

    # DATABASE CREATION
    def create_db(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({self.schema})")
        conn.commit()
        conn.close()

    def create_table(self, table_name: str, schema: Iterable):
        schema_sql = ", ".join(col.to_sql() for col in schema)
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql})")
        conn.commit()
        conn.close()

    # PARAMETERIZED EXECUTION
    def _execute_sql(self, sql: str, params=None):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        conn.close()

    def _fetchall_sql(self, sql: str, params=None):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        conn.close()
        return rows

    def _fetchone_sql(self, sql: str, params=None):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, params or [])
        row = cur.fetchone()
        conn.close()
        return row

    # ENABLE ENCRYPTION
    def encrypt(self, key: str):
        self._encryption_key = key
        print("Full database encryption enabled (SQLCipher).")
        return self

    # PUBLIC QUERY EXECUTION
    def run(self, builder: _QueryBuilder):
        sql, params = builder.to_sql()

        if builder._mode == "SELECT":
            return self._fetchall_sql(sql, params)

        self._execute_sql(sql, params)
        return None
