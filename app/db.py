## 4. Database schema and a small DB layer

# Design the SQLite schema: tables for **documents** 
# (e.g. `doc_id`, `title`, `source`, `created_at`), 
# **chunks** (e.g. `chunk_id`, `doc_id`, `chunk_index`, 
# `content`, `start_offset`, `end_offset`), and **embeddings** 
# (e.g. `chunk_id`, `model`, `vector_json`, `dim`). 
# 
# Add indexes that support “get chunks by doc_id” and 
# “get embedding by chunk_id.” Implement a thin DB module 
# that opens the DB, creates tables if they don’t exist, 
# and exposes a few helpers (e.g. insert document, insert chunks, 
# insert embeddings, fetch embeddings for retrieval). 
# Keep it synchronous and simple unless you already know you want async.

# can use app.state.dbconn for db conn since we will create that in main right before we call create db

import sqlite3
import json

def create_db(conn: sqlite3.Connection) -> sqlite3.Connection:
    #conn = app.state.dbconn    # sqlite3.connect("documentsdb.sqlite")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            created_at INTEGER,
            content_hash TEXT
        )
    """)
    try:
        conn.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT,
        chunk_index INTEGER,
        content TEXT,
        start_offset INTEGER,
        end_offset INTEGER
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        chunk_id TEXT PRIMARY KEY,
        model TEXT,
        vector_json TEXT,
        dim INTEGER
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id_chunk_index ON chunks(doc_id, chunk_index)
    """)

    # Financial tables (Private Cash Assistant)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            institution TEXT,
            document_id TEXT,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            description TEXT,
            principal REAL,
            rate_apr REAL,
            maturity_date TEXT,
            document_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS obligations (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            due_date TEXT NOT NULL,
            amount_estimate REAL,
            priority TEXT,
            document_id TEXT,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_events (
            id TEXT PRIMARY KEY,
            trigger_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_date TEXT,
            evaluated_at INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decision_history (
            id TEXT PRIMARY KEY,
            evaluated_at INTEGER NOT NULL,
            status TEXT NOT NULL,
            memo TEXT,
            trigger_ids TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_snapshots (
            id TEXT PRIMARY KEY,
            fetched_at INTEGER NOT NULL,
            product_type TEXT NOT NULL,
            term_months INTEGER,
            rate_apr REAL,
            source_url TEXT,
            source_name TEXT,
            quote TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_account_id ON positions(account_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_maturity ON positions(maturity_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obligations_due_date ON obligations(due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trigger_events_evaluated_at ON trigger_events(evaluated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_history_evaluated_at ON decision_history(evaluated_at)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_tags (
            doc_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (doc_id, tag),
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag)")

    conn.commit()

    return conn

# CRUD

def insert_document(conn,
    doc_id: str,
    created_at: int,
    title: str | None = None,
    source: str | None = None,
    content_hash: str | None = None,
    ) -> None:
    conn.execute(
        "INSERT INTO documents(doc_id, title, source, created_at, content_hash) VALUES (?,?,?,?,?)",
        (doc_id, title, source, created_at, content_hash),
    )


def find_doc_id_by_content_hash(conn: sqlite3.Connection, content_hash: str) -> str | None:
    """Return doc_id of an existing document with the same content hash, or None."""
    cursor = conn.execute(
        "SELECT doc_id FROM documents WHERE content_hash = ? LIMIT 1",
        (content_hash,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def insert_chunk(conn: sqlite3.Connection, 
    chunk_id: str,
    doc_id: str,
    chunk_index: int,
    content: str,
    start_offset: int,
    end_offset: int
    ) -> None:
    conn.execute("INSERT INTO chunks(chunk_id, doc_id, chunk_index, content, start_offset, end_offset) VALUES (?,?,?,?,?,?)", (chunk_id, doc_id, chunk_index, content, start_offset, end_offset),)
    # conn.commit()

def insert_embedding(conn: sqlite3.Connection, 
    chunk_id: str,
    model: str,
    vector_json: str,
    dim: int
    ) -> None:
    conn.execute("INSERT INTO embeddings(chunk_id, model, vector_json, dim) VALUES (?,?,?,?)", (chunk_id, model, vector_json, dim),)
    # conn.commit()

def doc_exist(
    conn: sqlite3.Connection,
    doc_id: str
    )->None:
    '''returns none if doc does not exist.  if it's a duplicate, raises 409'''
    cursor = conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,))
    return cursor.fetchone() is not None        # returns True if it finds one?

def get_embeddings_for_retrieval(conn, doc_id=None, doc_ids=None) -> list[tuple]:
    sql = """
    SELECT e.chunk_id, c.doc_id, e.vector_json, c.content
    FROM embeddings e
    JOIN chunks c ON e.chunk_id = c.chunk_id
    """
    if doc_ids is not None:
        if len(doc_ids) == 0:
            return []
        placeholders = ",".join("?" * len(doc_ids))
        cursor = conn.execute(sql + " WHERE c.doc_id IN (" + placeholders + ")", doc_ids)
    elif doc_id is not None:
        cursor = conn.execute(sql + " WHERE c.doc_id = ?", (doc_id,))
    else:
        cursor = conn.execute(sql)
    rows = cursor.fetchall()
    return [
        (chunk_id, doc_id, json.loads(vector_json), content)
        for chunk_id, doc_id, vector_json, content in rows
    ]


def delete_by_doc_id(conn: sqlite3.Connection, doc_id: str) -> None:
    conn.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_id,))
    conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM document_tags WHERE doc_id = ?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    conn.commit()


def set_document_tags(conn: sqlite3.Connection, doc_id: str, tags: list[str]) -> None:
    """Replace all tags for a document with the given list."""
    conn.execute("DELETE FROM document_tags WHERE doc_id = ?", (doc_id,))
    for tag in tags:
        tag = (tag or "").strip()
        if tag:
            conn.execute("INSERT INTO document_tags(doc_id, tag) VALUES (?, ?)", (doc_id, tag))


def get_document_tags(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    """Return list of tag strings for a document."""
    cursor = conn.execute("SELECT tag FROM document_tags WHERE doc_id = ? ORDER BY tag", (doc_id,))
    return [row[0] for row in cursor.fetchall()]


def get_doc_ids_by_tag(conn: sqlite3.Connection, tag: str) -> list[str]:
    """Return list of doc_ids that have the given tag."""
    cursor = conn.execute("SELECT doc_id FROM document_tags WHERE tag = ? ORDER BY doc_id", (tag.strip(),))
    return [row[0] for row in cursor.fetchall()]


def get_account_ids_by_document_id(conn: sqlite3.Connection, doc_id: str) -> list[str]:
    """Return list of account IDs that have document_id = doc_id."""
    cursor = conn.execute("SELECT id FROM accounts WHERE document_id = ? ORDER BY name", (doc_id,))
    return [row[0] for row in cursor.fetchall()]


def set_document_linked_account(
    conn: sqlite3.Connection, doc_id: str, account_id: str | None
) -> None:
    """Set which account links to this document. Clear all accounts with this doc_id, then set the given account's document_id if non-null."""
    conn.execute("UPDATE accounts SET document_id = NULL WHERE document_id = ?", (doc_id,))
    if account_id is not None:
        conn.execute("UPDATE accounts SET document_id = ? WHERE id = ?", (doc_id, account_id))


def list_documents(conn: sqlite3.Connection, snippet_max_len: int = 250) -> list[tuple]:
    """
    Returns list of (doc_id, title, source, created_at, num_chunks, snippet, tags, linked_account_ids).
    snippet is first chunk content truncated to snippet_max_len; None if no chunks.
    tags is list of tag strings; linked_account_ids is list of account IDs that reference this doc.
    Ordered by created_at desc.
    """
    sql = """
    SELECT
        d.doc_id,
        d.title,
        d.source,
        d.created_at,
        (SELECT COUNT(*) FROM chunks c WHERE c.doc_id = d.doc_id) AS num_chunks,
        (SELECT c.content FROM chunks c WHERE c.doc_id = d.doc_id ORDER BY c.chunk_index LIMIT 1) AS first_content
    FROM documents d
    ORDER BY d.created_at DESC
    """
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    result = []
    for doc_id, title, source, created_at, num_chunks, first_content in rows:
        snippet = None
        if first_content:
            snippet = first_content[:snippet_max_len] + ("..." if len(first_content) > snippet_max_len else "")
        tags = get_document_tags(conn, doc_id)
        linked_account_ids = get_account_ids_by_document_id(conn, doc_id)
        result.append((doc_id, title, source, created_at, num_chunks, snippet, tags, linked_account_ids))
    return result


# --- Financial (accounts, positions, obligations, triggers, decision_history) ---

def insert_account(
    conn: sqlite3.Connection,
    id: str,
    name: str,
    created_at: int,
    type: str | None = None,
    institution: str | None = None,
    document_id: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO accounts(id, name, type, institution, document_id, created_at) VALUES (?,?,?,?,?,?)",
        (id, name, type, institution, document_id, created_at),
    )


def list_accounts(conn: sqlite3.Connection) -> list[tuple]:
    cursor = conn.execute(
        "SELECT id, name, type, institution, document_id, created_at FROM accounts ORDER BY name"
    )
    return cursor.fetchall()


def get_account(conn: sqlite3.Connection, id: str) -> tuple | None:
    cursor = conn.execute(
        "SELECT id, name, type, institution, document_id, created_at FROM accounts WHERE id = ?",
        (id,),
    )
    return cursor.fetchone()


def update_account(
    conn: sqlite3.Connection,
    id: str,
    name: str | None = None,
    type: str | None = None,
    institution: str | None = None,
    document_id: str | None = None,
) -> None:
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if type is not None:
        updates.append("type = ?")
        params.append(type)
    if institution is not None:
        updates.append("institution = ?")
        params.append(institution)
    if document_id is not None:
        updates.append("document_id = ?")
        params.append(document_id)
    if not updates:
        return
    params.append(id)
    conn.execute(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", params)


def delete_account(conn: sqlite3.Connection, id: str) -> None:
    conn.execute("DELETE FROM positions WHERE account_id = ?", (id,))
    conn.execute("DELETE FROM accounts WHERE id = ?", (id,))


def insert_position(
    conn: sqlite3.Connection,
    id: str,
    account_id: str,
    asset_type: str,
    created_at: int,
    updated_at: int,
    description: str | None = None,
    principal: float | None = None,
    rate_apr: float | None = None,
    maturity_date: str | None = None,
    document_id: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO positions(id, account_id, asset_type, description, principal, rate_apr, maturity_date, document_id, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (id, account_id, asset_type, description, principal, rate_apr, maturity_date, document_id, created_at, updated_at),
    )


def list_positions(conn: sqlite3.Connection, account_id: str | None = None) -> list[tuple]:
    if account_id:
        cursor = conn.execute(
            "SELECT id, account_id, asset_type, description, principal, rate_apr, maturity_date, document_id, created_at, updated_at FROM positions WHERE account_id = ? ORDER BY maturity_date",
            (account_id,),
        )
    else:
        cursor = conn.execute(
            "SELECT id, account_id, asset_type, description, principal, rate_apr, maturity_date, document_id, created_at, updated_at FROM positions ORDER BY maturity_date"
        )
    return cursor.fetchall()


def get_position(conn: sqlite3.Connection, id: str) -> tuple | None:
    cursor = conn.execute(
        "SELECT id, account_id, asset_type, description, principal, rate_apr, maturity_date, document_id, created_at, updated_at FROM positions WHERE id = ?",
        (id,),
    )
    return cursor.fetchone()


def update_position(
    conn: sqlite3.Connection,
    id: str,
    updated_at: int,
    description: str | None = None,
    principal: float | None = None,
    rate_apr: float | None = None,
    maturity_date: str | None = None,
    document_id: str | None = None,
) -> None:
    updates = ["updated_at = ?"]
    params = [updated_at]
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if principal is not None:
        updates.append("principal = ?")
        params.append(principal)
    if rate_apr is not None:
        updates.append("rate_apr = ?")
        params.append(rate_apr)
    if maturity_date is not None:
        updates.append("maturity_date = ?")
        params.append(maturity_date)
    if document_id is not None:
        updates.append("document_id = ?")
        params.append(document_id)
    params.append(id)
    conn.execute(f"UPDATE positions SET {', '.join(updates)} WHERE id = ?", params)


def delete_position(conn: sqlite3.Connection, id: str) -> None:
    conn.execute("DELETE FROM positions WHERE id = ?", (id,))


def insert_obligation(
    conn: sqlite3.Connection,
    id: str,
    description: str,
    due_date: str,
    created_at: int,
    amount_estimate: float | None = None,
    priority: str | None = None,
    document_id: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO obligations(id, description, due_date, amount_estimate, priority, document_id, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (id, description, due_date, amount_estimate, priority, document_id, created_at),
    )


def list_obligations(conn: sqlite3.Connection) -> list[tuple]:
    cursor = conn.execute(
        "SELECT id, description, due_date, amount_estimate, priority, document_id, created_at FROM obligations ORDER BY due_date"
    )
    return cursor.fetchall()


def get_obligation(conn: sqlite3.Connection, id: str) -> tuple | None:
    cursor = conn.execute(
        "SELECT id, description, due_date, amount_estimate, priority, document_id, created_at FROM obligations WHERE id = ?",
        (id,),
    )
    return cursor.fetchone()


def update_obligation(
    conn: sqlite3.Connection,
    id: str,
    description: str | None = None,
    due_date: str | None = None,
    amount_estimate: float | None = None,
    priority: str | None = None,
    document_id: str | None = None,
) -> None:
    updates = []
    params = []
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if amount_estimate is not None:
        updates.append("amount_estimate = ?")
        params.append(amount_estimate)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    if document_id is not None:
        updates.append("document_id = ?")
        params.append(document_id)
    if not updates:
        return
    params.append(id)
    conn.execute(f"UPDATE obligations SET {', '.join(updates)} WHERE id = ?", params)


def delete_obligation(conn: sqlite3.Connection, id: str) -> None:
    conn.execute("DELETE FROM obligations WHERE id = ?", (id,))


def upsert_trigger_event(
    conn: sqlite3.Connection,
    id: str,
    trigger_type: str,
    entity_type: str,
    entity_id: str,
    evaluated_at: int,
    status: str,
    event_date: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO trigger_events(id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status)
           VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET event_date=excluded.event_date, evaluated_at=excluded.evaluated_at, status=excluded.status""",
        (id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status),
    )


def list_trigger_events(
    conn: sqlite3.Connection,
    status: str | None = None,
    since: int | None = None,
    limit: int = 100,
) -> list[tuple]:
    sql = "SELECT id, trigger_type, entity_type, entity_id, event_date, evaluated_at, status FROM trigger_events WHERE 1=1"
    params = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if since is not None:
        sql += " AND evaluated_at >= ?"
        params.append(since)
    sql += " ORDER BY evaluated_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(sql, params)
    return cursor.fetchall()


def insert_decision_history(
    conn: sqlite3.Connection,
    id: str,
    evaluated_at: int,
    status: str,
    memo: str | None = None,
    trigger_ids: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO decision_history(id, evaluated_at, status, memo, trigger_ids) VALUES (?,?,?,?,?)",
        (id, evaluated_at, status, memo, trigger_ids),
    )


def list_decision_history(
    conn: sqlite3.Connection,
    since: int | None = None,
    limit: int = 50,
) -> list[tuple]:
    sql = "SELECT id, evaluated_at, status, memo, trigger_ids FROM decision_history WHERE 1=1"
    params = []
    if since is not None:
        sql += " AND evaluated_at >= ?"
        params.append(since)
    sql += " ORDER BY evaluated_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(sql, params)
    return cursor.fetchall()


def insert_rate_snapshot(
    conn: sqlite3.Connection,
    id: str,
    fetched_at: int,
    product_type: str,
    rate_apr: float,
    term_months: int | None = None,
    source_url: str | None = None,
    source_name: str | None = None,
    quote: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO rate_snapshots(id, fetched_at, product_type, term_months, rate_apr, source_url, source_name, quote)
           VALUES (?,?,?,?,?,?,?,?)""",
        (id, fetched_at, product_type, term_months, rate_apr, source_url, source_name, quote),
    )


def get_latest_rate_snapshots(
    conn: sqlite3.Connection,
    product_type: str | None = None,
    term_months: int | None = None,
    limit: int = 10,
) -> list[tuple]:
    sql = "SELECT id, fetched_at, product_type, term_months, rate_apr, source_url, source_name, quote FROM rate_snapshots WHERE 1=1"
    params = []
    if product_type:
        sql += " AND product_type = ?"
        params.append(product_type)
    if term_months is not None:
        sql += " AND term_months = ?"
        params.append(term_months)
    sql += " ORDER BY fetched_at DESC LIMIT ?"
    params.append(limit)
    cursor = conn.execute(sql, params)
    return cursor.fetchall()
