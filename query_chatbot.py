#!/usr/bin/env python3
"""
Interactive Chatbot Query Demo using SDIT Scraped Knowledge
===========================================================
Demonstrates how to search and retrieve chatbot answers from
the generated sdit_chatbot_qa.json and sdit_chatbot_chunks.json.
"""

import json
import os
import re
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    qa_path = os.path.join(base_dir, "data", "sdit_chatbot_qa.json")
    kb_path = os.path.join(base_dir, "data", "sdit_chatbot_knowledge.json")

    with open(qa_path, "r", encoding="utf-8") as f:
        qa_data = json.load(f)

    with open(kb_path, "r", encoding="utf-8") as f:
        kb_data = json.load(f)

    return qa_data, kb_data


def query_qa(query: str, qa_data, top_k: int = 3):
    """Keyword and multi-question-variation scored retrieval over Q&A pairs."""
    STOP_WORDS = {
        "what", "who", "where", "when", "why", "how", "the", "and", "for",
        "are", "can", "you", "tell", "about", "there", "is", "in", "at", "to",
        "of", "from", "with", "have", "been", "does", "which", "give", "me"
    }
    query_terms = set(re.findall(r"\w+", query.lower())) - STOP_WORDS
    scored = []

    for item in qa_data:
        score = 0
        q_lower = item["question"].lower()
        a_lower = item["answer"].lower()
        vars_lower = [v.lower() for v in item.get("question_variations", [])]

        for term in query_terms:
            if len(term) <= 2:
                continue
            if term in q_lower:
                score += 4
            for var in vars_lower:
                if term in var:
                    score += 3
            if term in a_lower:
                score += 1

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:top_k]]


def main():
    print("=" * 65)
    print("      SDIT CHATBOT KNOWLEDGE RETRIEVAL DEMO")
    print("=" * 65)

    qa_data, kb_data = load_data()
    print(f"Loaded {len(kb_data['pages'])} pages and {len(qa_data)} Q&A pairs from data/.\n")

    sample_questions = [
        "What is the eligibility for Computer Science Engineering?",
        "Who are the top recruiters and what companies visit for placements?",
        "How can I contact Shree Devi Institute of Technology?",
        "What facilities and sports are available on campus?",
    ]

    for q in sample_questions:
        print(f"👤 User Question: {q}")
        matches = query_qa(q, qa_data, top_k=1)
        if matches:
            best = matches[0]
            print(f"🤖 Chatbot Answer ({best['category']}):")
            answer_preview = best["answer"].split("\n\n(Source:")[0]
            if len(answer_preview) > 250:
                answer_preview = answer_preview[:250] + "..."
            print(f"   {answer_preview}")
            print(f"   🔗 Source: {best['url']}")
        else:
            print("   No match found.")
        print("-" * 65)


if __name__ == "__main__":
    main()
