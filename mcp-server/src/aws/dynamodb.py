"""DynamoDB-backed CRM data store with SQLite fallback.

Wraps Amazon DynamoDB for CRM data storage. Falls back to SQLite when
AWS credentials are not available.

DynamoDB Schema:
    Table: sage-contacts
        PK: contact_id (String)
        Attributes: name, company, email, phone, title, notes, created_at, updated_at

    Table: sage-deals
        PK: deal_id (String)
        SK: contact_id (String)
        Attributes: title, value, stage, notes, sentiment, created_at, updated_at

    Table: sage-followups
        PK: followup_id (String)
        SK: contact_id (String)
        Attributes: title, due_date, completed, notes, created_at

    Table: sage-call-logs
        PK: log_id (String)
        Attributes: contact_id, deal_id, transcript, summary, duration_seconds,
                    sentiment, buying_signals, risks, created_at

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-1)
    DYNAMODB_TABLE_PREFIX: Table name prefix (default: sage)
"""

import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime


class DynamoDBStore:
    """DynamoDB-backed storage for CRM data with SQLite fallback.

    Provides the same interface as the SQLite Database class but uses
    DynamoDB when AWS credentials are available.
    """

    def __init__(
        self,
        region: str | None = None,
        table_prefix: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        db_path: str | None = None,
    ):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.table_prefix = table_prefix or os.environ.get("DYNAMODB_TABLE_PREFIX", "sage")
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self._use_fallback = not (self.aws_access_key and self.aws_secret_key)
        self._client = None
        self._resource = None

        # Fallback SQLite setup
        if self._use_fallback:
            self._db_path = db_path or os.path.join(tempfile.gettempdir(), "sage_dynamodb_fallback.db")
            self._init_fallback_db()

    @property
    def is_fallback(self) -> bool:
        """Return True if using SQLite fallback (no AWS credentials)."""
        return self._use_fallback

    def _get_resource(self):
        """Lazy-initialize the DynamoDB resource."""
        if self._resource is None:
            try:
                import boto3
                self._resource = boto3.resource(
                    "dynamodb",
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
            except ImportError:
                raise RuntimeError(
                    "boto3 is required for DynamoDB integration. "
                    "Install with: pip install boto3"
                )
        return self._resource

    def _table_name(self, logical_name: str) -> str:
        """Get the full DynamoDB table name."""
        return f"{self.table_prefix}-{logical_name}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def put_item(self, table: str, item: dict) -> bool:
        """Store an item in the specified table.

        Args:
            table: Logical table name (contacts, deals, followups, call_logs).
            item: Dictionary of attributes to store.

        Returns:
            True if the item was stored successfully.
        """
        if self._use_fallback:
            return self._fallback_put(table, item)

        try:
            dynamodb_table = self._get_resource().Table(self._table_name(table))
            # Ensure item has a primary key
            if "id" not in item:
                item["id"] = str(uuid.uuid4())
            dynamodb_table.put_item(Item=item)
            return True
        except Exception:
            return False

    def get_item(self, table: str, key: dict) -> dict:
        """Retrieve an item by its key.

        Args:
            table: Logical table name.
            key: Dictionary identifying the item (e.g., {"id": "123"}).

        Returns:
            The item as a dictionary, or empty dict if not found.
        """
        if self._use_fallback:
            return self._fallback_get(table, key)

        try:
            dynamodb_table = self._get_resource().Table(self._table_name(table))
            response = dynamodb_table.get_item(Key=key)
            return response.get("Item", {})
        except Exception:
            return {}

    def query_items(self, table: str, filter_expr: str) -> list:
        """Query items from a table with a filter expression.

        Args:
            table: Logical table name.
            filter_expr: Filter expression string (e.g., "company = :company").

        Returns:
            List of matching items.
        """
        if self._use_fallback:
            return self._fallback_query(table, filter_expr)

        try:
            dynamodb_table = self._get_resource().Table(self._table_name(table))
            # Simple scan with filter (DynamoDB query requires key conditions)
            response = dynamodb_table.scan()
            items = response.get("Items", [])
            # Apply simple filtering client-side for fallback compatibility
            return self._apply_filter(items, filter_expr)
        except Exception:
            return []

    def scan_items(self, table: str) -> list:
        """Scan all items from a table.

        Args:
            table: Logical table name.

        Returns:
            List of all items in the table.
        """
        if self._use_fallback:
            return self._fallback_scan(table)

        try:
            dynamodb_table = self._get_resource().Table(self._table_name(table))
            response = dynamodb_table.scan()
            return response.get("Items", [])
        except Exception:
            return []

    # ------------------------------------------------------------------
    # DynamoDB helpers
    # ------------------------------------------------------------------

    def _apply_filter(self, items: list, filter_expr: str) -> list:
        """Apply a simple filter expression to items client-side.

        Supports simple 'key = value' expressions.
        """
        if not filter_expr or "=" not in filter_expr:
            return items

        parts = filter_expr.split("=", 1)
        if len(parts) != 2:
            return items

        key = parts[0].strip()
        value = parts[1].strip().strip("'\"")

        return [item for item in items if str(item.get(key, "")) == value]

    # ------------------------------------------------------------------
    # SQLite Fallback
    # ------------------------------------------------------------------

    def _init_fallback_db(self):
        """Initialize the SQLite fallback database."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create tables matching DynamoDB logical names
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                company TEXT,
                email TEXT,
                phone TEXT,
                title TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS deals (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                title TEXT NOT NULL,
                value REAL,
                stage TEXT DEFAULT 'lead',
                notes TEXT,
                sentiment TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS followups (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                deal_id TEXT,
                title TEXT NOT NULL,
                due_date TEXT,
                completed INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS call_logs (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                deal_id TEXT,
                transcript TEXT,
                summary TEXT,
                duration_seconds INTEGER,
                sentiment TEXT,
                buying_signals TEXT,
                risks TEXT,
                created_at TEXT
            );
        """)
        conn.commit()
        conn.close()

    def _fallback_put(self, table: str, item: dict) -> bool:
        """Store item in SQLite fallback."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            if "id" not in item:
                item["id"] = str(uuid.uuid4())

            now = datetime.now().isoformat()
            if "created_at" not in item:
                item["created_at"] = now
            item["updated_at"] = now

            # Build dynamic INSERT based on table schema
            if table == "contacts":
                cursor.execute(
                    """INSERT OR REPLACE INTO contacts
                       (id, name, company, email, phone, title, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"], item.get("name"), item.get("company"),
                        item.get("email"), item.get("phone"), item.get("title"),
                        item.get("notes"), item["created_at"], item["updated_at"],
                    ),
                )
            elif table == "deals":
                cursor.execute(
                    """INSERT OR REPLACE INTO deals
                       (id, contact_id, title, value, stage, notes, sentiment, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"], item.get("contact_id"), item.get("title"),
                        item.get("value"), item.get("stage", "lead"),
                        item.get("notes"), item.get("sentiment"),
                        item["created_at"], item["updated_at"],
                    ),
                )
            elif table == "followups":
                cursor.execute(
                    """INSERT OR REPLACE INTO followups
                       (id, contact_id, deal_id, title, due_date, completed, notes, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"], item.get("contact_id"), item.get("deal_id"),
                        item.get("title"), item.get("due_date"),
                        item.get("completed", 0), item.get("notes"), item["created_at"],
                    ),
                )
            elif table == "call_logs":
                cursor.execute(
                    """INSERT OR REPLACE INTO call_logs
                       (id, contact_id, deal_id, transcript, summary, duration_seconds,
                        sentiment, buying_signals, risks, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["id"], item.get("contact_id"), item.get("deal_id"),
                        item.get("transcript"), item.get("summary"),
                        item.get("duration_seconds"), item.get("sentiment"),
                        json.dumps(item.get("buying_signals", [])),
                        json.dumps(item.get("risks", [])), item["created_at"],
                    ),
                )
            else:
                conn.close()
                return False

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def _fallback_get(self, table: str, key: dict) -> dict:
        """Retrieve item from SQLite fallback."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            item_id = key.get("id", "")
            cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                result = dict(row)
                # Deserialize JSON fields
                if table == "call_logs":
                    if result.get("buying_signals"):
                        result["buying_signals"] = json.loads(result["buying_signals"])
                    if result.get("risks"):
                        result["risks"] = json.loads(result["risks"])
                return result
            return {}
        except Exception:
            return {}

    def _fallback_query(self, table: str, filter_expr: str) -> list:
        """Query items from SQLite fallback."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Parse simple filter expression
            where_clause = ""
            params = []
            if filter_expr and "=" in filter_expr:
                parts = filter_expr.split("=", 1)
                key = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                where_clause = f"WHERE {key} = ?"
                params.append(value)

            cursor.execute(f"SELECT * FROM {table} {where_clause}", params)
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                item = dict(row)
                if table == "call_logs":
                    if item.get("buying_signals"):
                        item["buying_signals"] = json.loads(item["buying_signals"])
                    if item.get("risks"):
                        item["risks"] = json.loads(item["risks"])
                results.append(item)
            return results
        except Exception:
            return []

    def _fallback_scan(self, table: str) -> list:
        """Scan all items from SQLite fallback."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                item = dict(row)
                if table == "call_logs":
                    if item.get("buying_signals"):
                        item["buying_signals"] = json.loads(item["buying_signals"])
                    if item.get("risks"):
                        item["risks"] = json.loads(item["risks"])
                results.append(item)
            return results
        except Exception:
            return []
