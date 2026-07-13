from datetime import datetime, timezone

import sqlite_vec
from openai import OpenAI
from sqlalchemy import text

from config import settings
from storage import CategorizationExample, get_session

client = OpenAI(api_key=settings.openai_api_key)


def embed_text(value: str) -> bytes:
    """Embed a single string and return it as a serialized float32 byte vector."""
    response = client.embeddings.create(
        input=value,
        model="text-embedding-3-small"
    )

    return sqlite_vec.serialize_float32(response.data[0].embedding)


def embed_texts(values: list[str]) -> list[bytes]:
    """Embed a list of strings in a single API call and return serialized float32 byte vectors."""
    response = client.embeddings.create(
        input=values,
        model="text-embedding-3-small"
    )

    return [sqlite_vec.serialize_float32(d.embedding) for d in response.data]


def add_example(pattern: str, category: str, added_by: str) -> None:
    """
    Upsert a categorization example into the database with its embedding.

    If a record with the same remittance_pattern already exists, its category
    and embedding are updated in place. Otherwise a new record is inserted.
    """
    embedding = embed_text(pattern)
    example = CategorizationExample(
        remittance_pattern=pattern,
        correct_category=category,
        added_by=added_by,
        created_at=datetime.now(timezone.utc),
        embedding=embedding
    )

    with get_session() as session:
        existing = session.get(CategorizationExample, pattern)
        if existing:
            existing.correct_category = category
            existing.embedding = embedding
            session.commit()
        else:
            session.add(example)
            session.commit()


def find_similar_examples(remittance_strings: list[str], top_k: int = 5) -> dict[str, list[dict[str, str]]]:
    """
    For each remittance string, retrieve the top-k most similar categorization
    examples from the database using cosine distance on embeddings.

    Returns a dict mapping each input string to a list of
    {"pattern": ..., "category": ...} dicts ordered by ascending distance.
    """
    embeddings = embed_texts(remittance_strings)

    results: dict[str, list[dict[str, str]]] = {}

    with get_session() as session:
        for i, remittance in enumerate(remittance_strings):
            query_embedding = embeddings[i]

            rows = session.execute(
                text("""
                    SELECT remittance_pattern, correct_category
                     FROM categorization_examples
                     ORDER BY vec_distance_cosine(embedding, :embedding)
                     LIMIT :limit
                """),
                {"embedding": query_embedding, "limit": top_k}
            ).fetchall()

            results[remittance] = [{"pattern": r[0], "category": r[1]} for r in rows]

    return results
