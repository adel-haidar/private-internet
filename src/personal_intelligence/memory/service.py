import uuid
import json
import boto3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from psycopg2.extras import RealDictCursor

from personal_intelligence.config import get_settings
from personal_intelligence.database import _connect


@dataclass
class Memory:
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    memory_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _get_bedrock_client():
    s = get_settings()
    return boto3.client("bedrock-runtime", region_name=s.aws_region)


def _get_embedding(text: str) -> list[float]:
    bedrock = _get_bedrock_client()
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL,
            embedding vector(1024)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_memory(title: str, content: str, tags: list[str] | None = None) -> Memory:
    memory_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    tags = tags or []
    text = f"{title}\n{content}"
    embedding = _get_embedding(text)
    embedded_str = str(embedding).replace(" ", "")

    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO memories (memory_id, title, content, tags, created_at, embedding)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (memory_id, title, content, ",".join(tags), created_at, embedded_str),
    )
    conn.commit()
    cur.close()
    conn.close()

    return Memory(
        memory_id=memory_id,
        title=title,
        content=content,
        tags=tags,
        created_at=created_at,
    )


def fetch_memory(memory_id: str) -> Memory | None:
    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM memories WHERE memory_id = %s", (memory_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    return _row_to_memory(row)


def search_memories(query: str) -> list[Memory]:
    embedding = _get_embedding(query)

    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT *, embedding <=> %s::vector AS distance
           FROM memories
           ORDER BY distance
           LIMIT 5""",
        (str(embedding),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [_row_to_memory(row) for row in rows]


def list_memories(
    page: int = 1,
    page_size: int = 20,
    query: str | None = None,
) -> tuple[list[dict], int]:
    """Return paginated memory rows (id, title, tags, created_at, content) and total count."""
    offset = (page - 1) * page_size

    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if query:
        like = f"%{query}%"
        cur.execute(
            "SELECT COUNT(*) FROM memories WHERE title ILIKE %s OR tags ILIKE %s",
            (like, like),
        )
        total = cur.fetchone()["count"]
        cur.execute(
            """SELECT memory_id, title, tags, created_at, content
               FROM memories
               WHERE title ILIKE %s OR tags ILIKE %s
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (like, like, page_size, offset),
        )
    else:
        cur.execute("SELECT COUNT(*) FROM memories")
        total = cur.fetchone()["count"]
        cur.execute(
            """SELECT memory_id, title, tags, created_at, content
               FROM memories
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (page_size, offset),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    items = [
        {
            "id": row["memory_id"],
            "title": row["title"],
            "tags": [t.strip() for t in row["tags"].split(",") if t.strip()],
            "created_at": row["created_at"].isoformat(),
            "content": row["content"],
        }
        for row in rows
    ]
    return items, total


def _row_to_memory(row: Mapping[str, Any]) -> Memory:
    tags_raw = row["tags"]
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    return Memory(
        memory_id=row["memory_id"],
        title=row["title"],
        content=row["content"],
        tags=tags,
        created_at=row["created_at"],
    )
