import os
import sqlite3
from typing import Optional


class Database:
    def __init__(self, db_path: str = "sage.db", use_dynamodb: bool | None = None):
        self.db_path = db_path

        # DynamoDB integration: use when AWS credentials are available
        if use_dynamodb is None:
            use_dynamodb = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
        self._use_dynamodb = use_dynamodb
        self._dynamodb_store = None

        if not self._use_dynamodb:
            self._init_schema()

    @property
    def use_dynamodb(self) -> bool:
        """Return True if DynamoDB is enabled (AWS credentials available)."""
        return self._use_dynamodb

    def _get_dynamodb(self):
        """Lazy-initialize the DynamoDB store."""
        if self._dynamodb_store is None:
            from aws.dynamodb import DynamoDBStore
            self._dynamodb_store = DynamoDBStore()
        return self._dynamodb_store

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema = f.read()
        conn = self._get_conn()
        conn.executescript(schema)
        conn.close()

    def create_contact(self, data: dict) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO contacts (name, company, email, phone, title, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data.get("company"),
                data.get("email"),
                data.get("phone"),
                data.get("title"),
                data.get("notes"),
            ),
        )
        conn.commit()
        contact_id = cursor.lastrowid
        conn.close()
        return contact_id

    def get_contact(self, contact_id: int) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def create_deal(self, data: dict) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO deals (contact_id, title, value, stage, notes, sentiment)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.get("contact_id"),
                data["title"],
                data.get("value"),
                data.get("stage", "lead"),
                data.get("notes"),
                data.get("sentiment"),
            ),
        )
        conn.commit()
        deal_id = cursor.lastrowid
        conn.close()
        return deal_id

    def get_deal(self, deal_id: int) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM deals WHERE id = ?", (deal_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def search_contacts(self, query: str) -> list:
        conn = self._get_conn()
        pattern = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM contacts
               WHERE name LIKE ? OR company LIKE ? OR email LIKE ?""",
            (pattern, pattern, pattern),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_deals(self) -> list:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM deals").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_contacts(self) -> list:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM contacts").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_deal_stage(self, deal_id: int, stage: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE deals SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (stage, deal_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def get_followups_due(self) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM followups WHERE completed = 0"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def log_call(self, data: dict) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO call_logs
               (contact_id, deal_id, transcript, summary, duration_seconds, sentiment, buying_signals, risks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("contact_id"),
                data.get("deal_id"),
                data.get("transcript"),
                data.get("summary"),
                data.get("duration_seconds"),
                data.get("sentiment"),
                data.get("buying_signals"),
                data.get("risks"),
            ),
        )
        conn.commit()
        call_id = cursor.lastrowid
        conn.close()
        return call_id

    def get_contact_activities(self, contact_id: int) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM activities WHERE contact_id = ?", (contact_id,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_contact(self, contact_id: int, data: dict) -> bool:
        conn = self._get_conn()
        fields = []
        values = []
        for key, value in data.items():
            if key in ("name", "company", "email", "phone", "title", "notes"):
                fields.append(f"{key} = ?")
                values.append(value)
        if not fields:
            conn.close()
            return False
        values.append(contact_id)
        query = f"UPDATE contacts SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor = conn.execute(query, values)
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def create_followup(self, data: dict) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO followups (contact_id, deal_id, title, due_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data.get("contact_id"),
                data.get("deal_id"),
                data["title"],
                data.get("due_date"),
                data.get("notes"),
            ),
        )
        conn.commit()
        followup_id = cursor.lastrowid
        conn.close()
        return followup_id

    def get_call_logs(self) -> list:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM call_logs").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_followups(self) -> list:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM followups").fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_activities(self, contact_id: int = None, deal_id: int = None) -> list:
        """Get activities filtered by contact and/or deal."""
        conn = self._get_conn()
        query = "SELECT * FROM activities WHERE 1=1"
        params = []
        if contact_id is not None:
            query += " AND contact_id = ?"
            params.append(contact_id)
        if deal_id is not None:
            query += " AND deal_id = ?"
            params.append(deal_id)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_task(self, data: dict) -> int:
        """Create a general task."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO tasks (contact_id, deal_id, title, due_date, priority, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.get("contact_id"),
                data.get("deal_id"),
                data["title"],
                data.get("due_date"),
                data.get("priority", "medium"),
                data.get("notes"),
            ),
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return task_id

    def get_stage_history(self, deal_id: int) -> list:
        """Get stage history for a deal."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM stage_history WHERE deal_id = ? ORDER BY changed_at ASC",
            (deal_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_deal_interactions(self, deal_id: int) -> list:
        """Get all interactions (activities + call logs) for a deal."""
        conn = self._get_conn()
        activities = conn.execute(
            "SELECT * FROM activities WHERE deal_id = ? ORDER BY created_at DESC",
            (deal_id,),
        ).fetchall()
        call_logs = conn.execute(
            "SELECT * FROM call_logs WHERE deal_id = ? ORDER BY created_at DESC",
            (deal_id,),
        ).fetchall()
        conn.close()
        interactions = []
        for row in activities:
            interactions.append({**dict(row), "source": "activity"})
        for row in call_logs:
            interactions.append({**dict(row), "source": "call_log"})
        interactions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return interactions

    def get_deal_timeline(self, deal_id: int) -> list:
        """Get full timeline for a deal including stage changes and interactions."""
        conn = self._get_conn()
        stage_history = conn.execute(
            "SELECT * FROM stage_history WHERE deal_id = ? ORDER BY changed_at ASC",
            (deal_id,),
        ).fetchall()
        activities = conn.execute(
            "SELECT * FROM activities WHERE deal_id = ? ORDER BY created_at ASC",
            (deal_id,),
        ).fetchall()
        call_logs = conn.execute(
            "SELECT * FROM call_logs WHERE deal_id = ? ORDER BY created_at ASC",
            (deal_id,),
        ).fetchall()
        conn.close()
        timeline = []
        for row in stage_history:
            timeline.append({
                "type": "stage_change",
                "timestamp": row["changed_at"],
                "data": dict(row),
            })
        for row in activities:
            timeline.append({
                "type": "activity",
                "timestamp": row["created_at"],
                "data": dict(row),
            })
        for row in call_logs:
            timeline.append({
                "type": "call_log",
                "timestamp": row["created_at"],
                "data": dict(row),
            })
        timeline.sort(key=lambda x: x.get("timestamp", ""))
        return timeline

    # ------------------------------------------------------------------
    # DynamoDB delegation
    # ------------------------------------------------------------------

    def dynamodb_put(self, table: str, item: dict) -> bool:
        """Store an item in DynamoDB (when enabled).

        Args:
            table: Logical table name (contacts, deals, followups, call_logs).
            item: Dictionary of attributes to store.

        Returns:
            True if the item was stored successfully.
        """
        if not self._use_dynamodb:
            return False
        return self._get_dynamodb().put_item(table, item)

    def dynamodb_get(self, table: str, key: dict) -> dict:
        """Retrieve an item from DynamoDB by key (when enabled).

        Args:
            table: Logical table name.
            key: Dictionary identifying the item (e.g., {"id": "123"}).

        Returns:
            The item as a dictionary, or empty dict if not found.
        """
        if not self._use_dynamodb:
            return {}
        return self._get_dynamodb().get_item(table, key)

    def dynamodb_query(self, table: str, filter_expr: str) -> list:
        """Query items from DynamoDB with a filter expression (when enabled).

        Args:
            table: Logical table name.
            filter_expr: Filter expression string (e.g., "company = :company").

        Returns:
            List of matching items.
        """
        if not self._use_dynamodb:
            return []
        return self._get_dynamodb().query_items(table, filter_expr)

    def dynamodb_scan(self, table: str) -> list:
        """Scan all items from a DynamoDB table (when enabled).

        Args:
            table: Logical table name.

        Returns:
            List of all items in the table.
        """
        if not self._use_dynamodb:
            return []
        return self._get_dynamodb().scan_items(table)
