import json
from dataclasses import dataclass
from pathlib import Path

from . import config
from .errors import ChatbotError

MetadataValue = str | int


@dataclass(frozen=True)
class Document:
    id: str
    content: str
    metadata: dict[str, MetadataValue]


def load_documents(path: Path = config.CHUNKS_PATH) -> list[Document]:
    try:
        with path.open(encoding="utf-8") as file:
            records = json.load(file)
    except OSError as exc:
        raise ChatbotError("The knowledge base file could not be read.", 500) from exc
    except json.JSONDecodeError as exc:
        raise ChatbotError(
            "The knowledge base file contains invalid JSON.", 500
        ) from exc

    if not isinstance(records, list):
        raise ChatbotError("The knowledge base must contain a list of records.", 500)

    documents = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ChatbotError(f"Knowledge record {index} must be an object.", 500)

        record_id = record.get("id")
        content = record.get("content")
        if not isinstance(record_id, str) or not record_id.strip():
            raise ChatbotError(f"Knowledge record {index} has no valid ID.", 500)
        if not isinstance(content, str) or not content.strip():
            raise ChatbotError(f"Knowledge record {record_id} has no content.", 500)

        metadata: dict[str, MetadataValue] = {}
        for key in ("url", "title", "category", "heading", "word_count"):
            if key not in record:
                continue
            value = record[key]
            if not isinstance(value, (str, int)):
                raise ChatbotError(
                    f"Knowledge record {record_id} has invalid {key} metadata.",
                    500,
                )
            metadata[key] = value

        documents.append(
            Document(
                id=record_id,
                content=content.strip(),
                metadata=metadata,
            )
        )

    return documents
