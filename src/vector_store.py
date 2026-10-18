import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .documents import Document


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float


class SQLiteVectorStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def upsert(self, document: Document, embedding: Sequence[float]) -> None:
        vector = self._validated_vector(embedding)
        self._connection.execute(
            """
            INSERT INTO vectors (id, content, metadata, embedding)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content = excluded.content,
                metadata = excluded.metadata,
                embedding = excluded.embedding
            """,
            (
                document.id,
                document.content,
                json.dumps(document.metadata),
                json.dumps(vector),
            ),
        )
        self._connection.commit()

    def search(
        self,
        embedding: Sequence[float],
        limit: int = 5,
    ) -> list[SearchResult]:
        query = self._validated_vector(embedding)
        if limit < 1:
            raise ValueError("limit must be positive")

        results = []
        rows = self._connection.execute(
            "SELECT id, content, metadata, embedding FROM vectors"
        )
        for record_id, content, metadata_json, embedding_json in rows:
            vector = json.loads(embedding_json)
            if len(vector) != len(query):
                raise ValueError("stored embeddings must have a consistent dimension")
            score = self._cosine_similarity(query, vector)
            results.append(
                SearchResult(
                    document=Document(
                        id=record_id,
                        content=content,
                        metadata=json.loads(metadata_json),
                    ),
                    score=score,
                )
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    @staticmethod
    def _validated_vector(values: Sequence[float]) -> list[float]:
        vector = list(values)
        if not vector or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError("embedding must contain finite numeric values")
        return [float(value) for value in vector]

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
