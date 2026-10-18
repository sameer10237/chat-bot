# SDIT Chatbot Data Scraper

A specialized Python scraper designed to harvest, clean, and structure institutional data from [Shree Devi Institute of Technology (SDIT)](https://sdit.ac.in/) into clean JSON formats for AI chatbots, Retrieval-Augmented Generation (RAG) vector stores, and FAQ systems.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Dependencies: `httpx>=0.28.0`, `beautifulsoup4>=4.12.0`)*

### 2. Run the Scraper
To scrape all data and export all 3 chatbot JSON datasets into `./data/`:
```bash
python sdit_scraper.py
```
*(On Windows systems, you can also run `py sdit_scraper.py`)*

---

## ⚙️ Command-Line Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--output-dir` | `data` | Directory where output JSON files will be saved |
| `--workers` | `5` | Number of concurrent scraper threads |
| `--delay` | `0.2` | Delay in seconds between requests (prevents rate limits) |
| `--max-pages` | `None` | Optional limit on total pages scraped (for rapid testing) |
| `--no-chunks` | `False` | Omit the RAG chunk JSON file |
| `--no-qa` | `False` | Omit the Q&A dataset JSON file |

#### Example: Rapid Test (first 5 pages)
```bash
python sdit_scraper.py --max-pages 5 --output-dir ./test_data
```

---

## 📦 Generated Output Files

The scraper produces three clean, ready-to-use JSON files in the `data/` folder:

### 1. `sdit_chatbot_knowledge.json` (Master Knowledge Base)
The master repository containing full hierarchical page records.
```json
{
  "metadata": {
    "institution_name": "Shree Devi Institute of Technology (SDIT)",
    "website": "https://sdit.ac.in",
    "scraped_at": "2026-09-07T17:45:00Z",
    "total_pages": 49,
    "total_sections": 210,
    "total_word_count": 35000,
    "categories": [
      "About SDIT & Governance",
      "Academics & Departments",
      "Admissions & Eligibility",
      "Campus & Facilities",
      "Contact & Support",
      "Placements & Careers"
    ]
  },
  "pages": [
    {
      "url": "https://sdit.ac.in/computer-science-engineering/",
      "title": "Computer Science & Engineering",
      "category": "Academics & Departments",
      "meta_description": "...",
      "contacts": { "emails": [...], "phone_numbers": [...] },
      "sections_count": 8,
      "word_count": 850,
      "sections": [
        {
          "heading": "Overview",
          "level": 2,
          "paragraphs": ["..."],
          "bullet_points": [["..."]],
          "tables": []
        }
      ],
      "full_content": "## Overview\n\n..."
    }
  ]
}
```

### 2. `sdit_chatbot_chunks.json` (RAG Vector Database Ready)
Pre-chunked semantic passages (200-300 words) with source metadata, ready for vector embedding (e.g. ChromaDB, FAISS, Pinecone, LangChain, LlamaIndex):
```json
[
  {
    "id": "sdit-chunk-0001",
    "url": "https://sdit.ac.in/computer-science-engineering/",
    "title": "Computer Science & Engineering",
    "category": "Academics & Departments",
    "heading": "Eligibility",
    "content": "Document: Computer Science & Engineering | Section: Eligibility\n\nPre-University Board or any other examinations recognized by the University...",
    "word_count": 145
  }
]
```

### 3. `sdit_chatbot_qa.json` (Curated Multi-Form Q&A FAQ Dataset)
Curated Question-and-Answer pairs with multiple realistic question variations (conversational student inquiries, direct qualification checks, formal inquiries, and keyword search phrasings), ideal for intent matching, FAQ bots, and fine-tuning:
```json
[
  {
    "id": "sdit-qa-0007",
    "question": "What are the achievements and evidence of success in SDIT's best practices?",
    "question_variations": [
      "How successful has SDIT been in implementing environmental sustainability and green initiatives?",
      "What awards, audit rankings, or certifications has SDIT earned for its best practices?",
      "Tell me about the outcomes of SDIT's sustainability, green audit results, and eco-initiatives.",
      "Has Shree Devi Institute of Technology won any awards or rankings for green campus practices?",
      "SDIT best practices evidence of success and audit achievements"
    ],
    "section": "Evidence of Success",
    "category": "About SDIT & Governance",
    "answer": "- Achieved Gold Ranking as a Green College by meeting Green Mentors’ Accreditation Standards for Global Readiness...\n\n(Source: https://sdit.ac.in/best-practices/)",
    "url": "https://sdit.ac.in/best-practices/"
  }
]
```

---

## 🤖 How to Integrate with a Chatbot (Example)

### Basic Python Query / RAG Example
```python
import json

# 1. Load the knowledge base
with open("data/sdit_chatbot_knowledge.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

# 2. Simple keyword search over all pages
def search_sdit(query: str):
    query = query.lower()
    matches = []
    for page in kb["pages"]:
        if query in page["full_content"].lower() or query in page["title"].lower():
            matches.append({
                "title": page["title"],
                "category": page["category"],
                "url": page["url"]
            })
    return matches

print(search_sdit("placement"))
```

### Ingestion into Vector Stores (ChromaDB / LangChain)
```python
import json
from langchain_core.documents import Document

with open("data/sdit_chatbot_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# Convert to LangChain Document objects
documents = [
    Document(
        page_content=c["content"],
        metadata={
            "id": c["id"],
            "url": c["url"],
            "title": c["title"],
            "category": c["category"],
            "heading": c["heading"]
        }
    )
    for c in chunks
]

# Add to your vector store (e.g. Chroma, FAISS, Pinecone)
# vector_store = Chroma.from_documents(documents, embedding_model)
```

## Chatbot Conversation Memory

The application keeps conversation history as ordered user/assistant message
pairs. `ConversationMemory` provides a bounded in-memory buffer, and the LLM
controller trims older complete exchanges before building a provider request.
The default context budget is 6,000 estimated tokens and can be changed with
`MAX_CONTEXT_TOKENS`.

Token counts are estimates based on UTF-8 byte length, not a provider-specific
tokenizer. A request is rejected if its system prompt and current message alone
exceed the configured budget. Conversation buffers are process-local and are
not persisted between sessions or application restarts.
