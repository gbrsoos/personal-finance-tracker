from config import settings
from openai import OpenAI
import sqlite_vec
from storage import get_session, CategorizationExample
from datetime import datetime, timezone
from sqlalchemy import text

client = OpenAI(api_key=settings.openai_api_key)


def embed_text(text: str | list[str]) -> bytes | list[bytes]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    if isinstance(text, str):
        return sqlite_vec.serialize_float32(response.data[0].embedding)
    else:
        return [sqlite_vec.serialize_float32(d.embedding) for d in response.data]


def add_example(pattern: str, category: str, added_by: str):
    embedding = embed_text(pattern)  # embed immediately
    example = CategorizationExample(
        remittance_pattern=pattern,
        correct_category=category,
        added_by=added_by,
        created_at=datetime.now(timezone.utc),
        embedding=embedding
    )

    with get_session() as session:
        session.add(example)
        session.commit()


def find_similar_examples(remittance_strings: list[str], top_k=5) -> dict[str, list]:
    embeddings = embed_text(remittance_strings)

    results = {}

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
