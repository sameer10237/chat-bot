#!/usr/bin/env python3
"""
SDIT Chatbot Data Scraper
=========================
A robust scraper tailored for Shree Devi Institute of Technology (https://sdit.ac.in/).
Harvests, cleans, and structures institutional data into JSON formats ready for LLM chatbots,
vector databases (RAG), and FAQ systems.

Author: Antigravity
"""

import argparse
import concurrent.futures
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sdit_scraper")

BASE_URL = "https://sdit.ac.in"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (SDIT-Chatbot-Scraper)"
)

# File extensions to ignore during crawling
IGNORED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot"
}


def clean_text(text: Optional[str]) -> str:
    """Clean and normalize whitespace, removing zero-width characters."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\u200b", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_contact_info(text: str) -> Dict[str, List[str]]:
    """Extract emails and phone numbers from raw text using regex."""
    emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)))
    # Clean trailing punctuation from emails
    clean_emails = [e.rstrip(".,;") for e in emails if "." in e.split("@")[-1]]

    raw_phones = re.findall(r"(?:\+91[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{6,8}", text)
    clean_phones = set()
    for p in raw_phones:
        digits = re.sub(r"\D", "", p)
        # Indian landlines or mobile numbers typically have 10-12 digits
        if 10 <= len(digits) <= 12 and not digits.startswith(("2020", "2021", "2022", "2023", "2024", "2025", "2026")):
            clean_phones.add(p.strip())

    return {
        "emails": sorted(clean_emails),
        "phone_numbers": sorted(clean_phones),
    }


def categorize_page(url: str, title: str) -> str:
    """Categorize an SDIT page into a domain category for chatbot topic routing."""
    url_lower = url.lower()
    title_lower = title.lower()

    if any(k in url_lower for k in [
        "engineering", "artificial-intelligence", "m-tech", "master-of",
        "phd", "research-centre", "cse", "ise", "ece", "civil", "mechanical"
    ]):
        return "Academics & Departments"
    elif any(k in url_lower for k in [
        "eligibility", "apply", "application", "scholarship", "brochure", "admission"
    ]):
        return "Admissions & Eligibility"
    elif any(k in url_lower for k in [
        "placement", "tpo", "progression", "industrial-explosure", "recruit"
    ]):
        return "Placements & Careers"
    elif any(k in url_lower for k in [
        "campus", "infrastructure", "sports", "clubs", "facilities", "location", "hostel", "library"
    ]):
        return "Campus & Facilities"
    elif any(k in url_lower for k in [
        "contact", "feedback", "location", "reach"
    ]):
        return "Contact & Support"
    elif any(k in url_lower for k in [
        "about", "vision", "principals", "administrator", "governing", "iqac",
        "naac", "nirf", "affiliation", "strategic", "best-practices", "ssr", "committees"
    ]):
        return "About SDIT & Governance"
    return "General Information"


class SDITScraper:
    """High-performance scraper for Shree Devi Institute of Technology."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 0.2,
        max_workers: int = 5,
        timeout: float = 15.0,
        max_pages: Optional[int] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_pages = max_pages
        self.client = httpx.Client(
            headers={"User-Agent": DEFAULT_USER_AGENT},
            timeout=self.timeout,
            follow_redirects=True,
        )

    def close(self):
        self.client.close()

    def discover_urls(self) -> List[str]:
        """
        Discover all institutional pages via:
        1. WordPress REST API (/wp-json/wp/v2/pages)
        2. Yoast SEO XML Sitemaps (page-sitemap.xml, sitemap_index.xml)
        3. Homepage and navigation link crawling
        """
        discovered: Set[str] = set()
        logger.info("🔍 Discovering URLs across SDIT website...")

        # 1. Check WordPress REST API
        try:
            logger.info("Checking WordPress REST API (/wp-json/wp/v2/pages)...")
            page = 1
            while True:
                resp = self.client.get(f"{self.base_url}/wp-json/wp/v2/pages?per_page=100&page={page}")
                if resp.status_code != 200:
                    break
                items = resp.json()
                if not items or not isinstance(items, list):
                    break
                for item in items:
                    link = item.get("link")
                    if link and self._is_valid_internal_url(link):
                        discovered.add(self._normalize_url(link))
                page += 1
            logger.info(f"REST API yielded {len(discovered)} pages.")
        except Exception as e:
            logger.warning(f"Could not fetch REST API pages: {e}")

        # 2. Check XML Sitemaps
        sitemap_endpoints = [
            f"{self.base_url}/page-sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
        ]
        for sitemap_url in sitemap_endpoints:
            try:
                logger.info(f"Checking sitemap: {sitemap_url}")
                resp = self.client.get(sitemap_url)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                        url = loc.text.strip() if loc.text else ""
                        if url.endswith(".xml"):
                            continue  # Sub-sitemaps
                        if self._is_valid_internal_url(url):
                            discovered.add(self._normalize_url(url))
            except Exception as e:
                logger.warning(f"Error parsing sitemap {sitemap_url}: {e}")

        # 3. Crawl Homepage for additional links
        try:
            logger.info(f"Crawling homepage links from {self.base_url}...")
            resp = self.client.get(self.base_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    full_url = urljoin(self.base_url, a["href"])
                    if self._is_valid_internal_url(full_url):
                        discovered.add(self._normalize_url(full_url))
        except Exception as e:
            logger.warning(f"Error crawling homepage: {e}")

        # Ensure home page is in the list
        discovered.add(f"{self.base_url}/")

        sorted_urls = sorted(discovered)
        if self.max_pages:
            sorted_urls = sorted_urls[: self.max_pages]

        logger.info(f"✅ Discovered {len(sorted_urls)} target URLs for scraping.")
        return sorted_urls

    def _is_valid_internal_url(self, url: str) -> bool:
        """Filter out external links, media files, wp-admin, and spam pagination."""
        parsed = urlparse(url)
        base_domain = urlparse(self.base_url).netloc
        if parsed.netloc != base_domain:
            return False

        path_lower = parsed.path.lower()

        # Check ignored file extensions
        if any(path_lower.endswith(ext) for ext in IGNORED_EXTENSIONS):
            return False

        # Exclude administrative / technical / feed endpoints
        excluded_patterns = [
            "/wp-admin", "/wp-login", "/wp-includes", "/wp-json",
            "/feed", "/comments/feed", "/xmlrpc.php",
            "/author/", "/tag/", "/category/page/",
            "/sample-page"  # Default blank sample page
        ]
        if any(pattern in path_lower for pattern in excluded_patterns):
            return False

        return True

    def _normalize_url(self, url: str) -> str:
        """Strip query params, hash fragments, and normalize trailing slash."""
        parsed = urlparse(url)
        path = parsed.path
        if not path.endswith("/"):
            path += "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def parse_page(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Parse raw HTML into clean, structured chatbot data."""
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Page Title
        raw_title = soup.title.string.strip() if soup.title and soup.title.string else ""
        # Remove common repeating suffixes
        title = re.sub(
            r"\s*\|\s*Shree Devi Institute.*$", "", raw_title, flags=re.IGNORECASE
        ).strip()
        title = re.sub(
            r"\s*-\s*Shree Devi Institute.*$", "", title, flags=re.IGNORECASE
        ).strip()
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else urlparse(url).path.strip("/").replace("-", " ").title()

        # 2. Extract Meta Description
        meta_description = ""
        meta_el = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", attrs={"property": "og:description"}
        )
        if meta_el and meta_el.get("content"):
            meta_description = clean_text(meta_el["content"])

        # 3. Clean DOM (Strip Boilerplate)
        for tag in soup(
            ["header", "footer", "nav", "script", "style", "noscript", "iframe", "svg", "canvas"]
        ):
            tag.decompose()

        for el in soup.find_all(
            class_=[
                "top-info", "top-det", "top-apply", "sidebar-wrapper",
                "back_to_top", "page-sidebar", "widget", "social-icons"
            ]
        ):
            el.decompose()

        for el in soup.find_all(id=["back_to_top", "sidebar-wrapper", "header"]):
            el.decompose()

        # Target primary content container
        content_container = (
            soup.find(class_="inside-pages")
            or soup.find(class_="in-about1")
            or soup.find(class_="in-bg")
            or soup.find("article")
            or soup.body
        )
        if not content_container:
            return None

        # 4. Extract Structured Sections
        sections: List[Dict[str, Any]] = []
        current_section: Dict[str, Any] = {
            "heading": "Overview",
            "level": 1,
            "paragraphs": [],
            "bullet_points": [],
            "tables": [],
        }

        # Elements to traverse sequentially
        for elem in content_container.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "table"]
        ):
            tag_name = elem.name
            if tag_name.startswith("h"):
                h_text = clean_text(elem.get_text())
                if h_text and len(h_text) > 1:
                    # Save current section if it has any content
                    if (
                        current_section["paragraphs"]
                        or current_section["bullet_points"]
                        or current_section["tables"]
                    ):
                        sections.append(current_section)

                    try:
                        level = int(tag_name[1])
                    except ValueError:
                        level = 2

                    current_section = {
                        "heading": h_text,
                        "level": level,
                        "paragraphs": [],
                        "bullet_points": [],
                        "tables": [],
                    }

            elif tag_name == "p":
                p_text = clean_text(elem.get_text())
                # Ignore breadcrumbs and tiny fragments
                if p_text and len(p_text) > 15 and not p_text.startswith("Home »"):
                    # Avoid duplicate paragraphs in the same section
                    if p_text not in current_section["paragraphs"]:
                        current_section["paragraphs"].append(p_text)

            elif tag_name in ["ul", "ol"]:
                items = []
                for li in elem.find_all("li", recursive=False):
                    li_text = clean_text(li.get_text())
                    if li_text and len(li_text) > 2:
                        items.append(li_text)
                if items:
                    current_section["bullet_points"].append(items)

            elif tag_name == "table":
                table_rows = []
                for tr in elem.find_all("tr"):
                    cols = [clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
                    if any(cols):
                        table_rows.append(cols)
                if table_rows:
                    current_section["tables"].append(table_rows)

        if (
            current_section["paragraphs"]
            or current_section["bullet_points"]
            or current_section["tables"]
        ):
            sections.append(current_section)

        # 5. Full text & Contact Information
        full_text_parts = []
        for s in sections:
            full_text_parts.append(f"## {s['heading']}")
            for p in s["paragraphs"]:
                full_text_parts.append(p)
            for b_list in s["bullet_points"]:
                for item in b_list:
                    full_text_parts.append(f"- {item}")
            for tbl in s["tables"]:
                for row in tbl:
                    full_text_parts.append(" | ".join(row))

        full_text = "\n\n".join(full_text_parts)
        if len(full_text.strip()) < 50:
            # Page has virtually no text content (e.g. empty image placeholder)
            return None

        contacts = extract_contact_info(full_text)
        category = categorize_page(url, title)

        return {
            "url": url,
            "title": title,
            "category": category,
            "meta_description": meta_description,
            "contacts": contacts,
            "sections_count": len(sections),
            "word_count": len(full_text.split()),
            "sections": sections,
            "full_content": full_text,
        }

    def scrape_single(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single URL with error handling."""
        try:
            time.sleep(self.delay)
            resp = self.client.get(url)
            if resp.status_code == 200:
                return self.parse_page(url, resp.text)
            else:
                logger.warning(f"Failed to fetch {url} (HTTP {resp.status_code})")
                return None
        except Exception as e:
            logger.error(f"Exception while scraping {url}: {e}")
            return None

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrape all discovered URLs using a thread pool."""
        urls = self.discover_urls()
        total_urls = len(urls)
        logger.info(f"🚀 Starting scrape of {total_urls} URLs with {self.max_workers} workers...")

        results: List[Dict[str, Any]] = []
        completed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_single, url): url for url in urls}

            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                completed += 1
                try:
                    page_data = future.result()
                    if page_data:
                        results.append(page_data)
                        logger.info(
                            f"[{completed}/{total_urls}] ✅ {page_data['title']} ({page_data['word_count']} words)"
                        )
                    else:
                        logger.info(f"[{completed}/{total_urls}] ⚠️ Skipped low-content page: {url}")
                except Exception as exc:
                    logger.error(f"[{completed}/{total_urls}] ❌ {url} generated exception: {exc}")

        # Sort results alphabetically by category then title
        results.sort(key=lambda x: (x["category"], x["title"]))
        logger.info(f"🎉 Scraping complete! Successfully structured {len(results)} pages.")
        return results


def build_rag_chunks(pages: List[Dict[str, Any]], chunk_size_words: int = 300) -> List[Dict[str, Any]]:
    """
    Split structured pages into semantic, vector-DB ready chunks.
    Each chunk retains page title, section heading, URL, and category for citation.
    """
    chunks: List[Dict[str, Any]] = []
    chunk_id = 1

    for page in pages:
        url = page["url"]
        title = page["title"]
        category = page["category"]

        for s_idx, section in enumerate(page["sections"]):
            heading = section["heading"]
            lines = []

            for p in section["paragraphs"]:
                lines.append(p)
            for b_list in section["bullet_points"]:
                for item in b_list:
                    lines.append(f"• {item}")
            for tbl in section["tables"]:
                for row in tbl:
                    lines.append(" | ".join(row))

            sec_text = "\n".join(lines).strip()
            if not sec_text:
                continue

            words = sec_text.split()
            # If section is small, keep as single chunk
            if len(words) <= chunk_size_words:
                chunks.append({
                    "id": f"sdit-chunk-{chunk_id:04d}",
                    "url": url,
                    "title": title,
                    "category": category,
                    "heading": heading,
                    "content": f"Document: {title} | Section: {heading}\n\n{sec_text}",
                    "word_count": len(words),
                })
                chunk_id += 1
            else:
                # Split large section into overlapping chunks
                stride = chunk_size_words - 50
                for start in range(0, len(words), stride):
                    sub_words = words[start : start + chunk_size_words]
                    if len(sub_words) < 30 and start > 0:
                        break
                    sub_text = " ".join(sub_words)
                    chunks.append({
                        "id": f"sdit-chunk-{chunk_id:04d}",
                        "url": url,
                        "title": title,
                        "category": category,
                        "heading": heading,
                        "content": f"Document: {title} | Section: {heading} (Part {start // stride + 1})\n\n{sub_text}",
                        "word_count": len(sub_words),
                    })
                    chunk_id += 1

    return chunks


def clean_heading_for_qa(heading: str) -> str:
    """Strip colons, asterisks, and whitespace from section headings."""
    return re.sub(r"[:\*\s]+$", "", heading).strip()


def generate_multi_form_questions(
    title: str,
    heading: str,
    category: str,
    content: str,
    url: str
) -> Tuple[str, List[str]]:
    """
    Generate a primary natural question and multiple diverse variations across:
    - Direct / Requirements inquiry
    - Conversational student question
    - Action / Outcome inquiry
    - Concise keyword search format
    - Alternative angle / Synonym inquiry
    """
    h_clean = clean_heading_for_qa(heading)
    h_lower = h_clean.lower()
    t_clean = re.sub(r"\s*\|\s*.*$", "", title).strip()
    t_clean = re.sub(r"\s*-\s*.*$", "", t_clean).strip()
    t_lower = t_clean.lower()
    c_lower = content.lower()

    # 1. Best Practices
    if "best practice" in t_lower:
        if "evidence of success" in h_lower or "evidence" in h_lower:
            primary = "What are the achievements and evidence of success in SDIT's best practices?"
            variations = [
                "How successful has SDIT been in implementing environmental sustainability and green initiatives?",
                "What awards, audit rankings, or certifications has SDIT earned for its best practices?",
                "Tell me about the outcomes of SDIT's sustainability, green audit results, and eco-initiatives.",
                "Has Shree Devi Institute of Technology won any awards or rankings for green campus practices?",
                "SDIT best practices evidence of success and audit achievements"
            ]
        elif "problem" in h_lower or "resource" in h_lower:
            primary = "What challenges and resource requirements were faced in implementing SDIT's best practices?"
            variations = [
                "What difficulties does SDIT encounter while executing campus sustainability and social initiatives?",
                "Tell me about the logistical, financial, or scheduling problems faced in SDIT's best practices.",
                "What resources are required to overcome obstacles in SDIT's sustainability initiatives?",
                "SDIT best practices challenges, obstacles, and resource requirements"
            ]
        elif "objective" in h_lower or "aim" in h_lower:
            primary = "What are the main objectives and goals of the best practices at SDIT?"
            variations = [
                "Why did SDIT introduce its best practices and social responsibility initiatives?",
                "What values and social outcomes does SDIT aim to achieve through its best practices?",
                "Tell me the key objectives of environmental and community best practices at SDIT.",
                "SDIT best practices objectives, purpose, and community impact"
            ]
        elif "context" in h_lower:
            primary = "What is the context and background of the best practices at SDIT?"
            variations = [
                "What led to the implementation of green and community best practices at SDIT?",
                "Explain the background and institutional context of SDIT's best practices.",
                "SDIT best practices background, institutional context, and need"
            ]
        elif "practice" in h_lower:
            primary = "What specific environmental and social best practices are conducted at SDIT?"
            variations = [
                "How does Shree Devi Institute of Technology implement its green campus and social practices?",
                "What sustainable initiatives like solar power, waste management, or rainwater harvesting exist at SDIT?",
                "Tell me how SDIT carries out its best practices in campus life.",
                "SDIT green campus initiatives, solar energy, and sustainable practices"
            ]
        else:
            primary = f"What details are provided about {h_clean} in SDIT's best practices?"
            variations = [
                f"Tell me about {h_clean} regarding best practices at Shree Devi Institute of Technology.",
                f"How does {h_clean} contribute to best practices at SDIT?",
                f"SDIT best practices {h_clean} details"
            ]

    # 2. Institutional Distinctiveness / SHAPE Model
    elif "distinctiveness" in t_lower or "shape" in h_lower or "shape" in c_lower:
        if "shape model" in h_lower or "shape model" in c_lower:
            primary = "What is the SHAPE Model and how does it enhance student quality at SDIT?"
            variations = [
                "Explain the SHAPE framework used at Shree Devi Institute of Technology.",
                "How does SDIT develop professional, soft, and technical skills using the SHAPE model?",
                "Tell me about the SHAPE model for holistic student development at SDIT.",
                "SDIT SHAPE model framework, components, and student training"
            ]
        elif "component" in h_lower:
            primary = "What are the key components of the SHAPE Model at SDIT?"
            variations = [
                "What does each letter in the SHAPE model stand for at Shree Devi Institute of Technology?",
                "Explain Soft Skills, Human Values, Add-on Courses, Personality, and Technical Skills at SDIT.",
                "Break down the 5 pillars of the SHAPE model at SDIT.",
                "SDIT SHAPE model components, pillars, and curriculum integration"
            ]
        elif any(yr in h_lower for yr in ["first year", "second year", "third year", "fourth year"]):
            primary = f"What training programs are conducted during the {h_clean} under SDIT's SHAPE Model?"
            variations = [
                f"How are {h_clean} students trained in aptitude, soft skills, and technical certificates at SDIT?",
                f"Tell me about the curriculum and personality development modules for {h_clean} at SDIT.",
                f"SDIT {h_clean} training schedule, aptitude classes, and soft skills"
            ]
        else:
            primary = "What is the institutional distinctiveness of Shree Devi Institute of Technology?"
            variations = [
                "What makes SDIT unique in its approach to technical education and student employability?",
                "Tell me about SDIT's distinct educational model and career development culture.",
                "SDIT institutional distinctiveness and student enhancement approach"
            ]

    # 3. Academic Departments
    elif category == "Academics & Departments":
        if "eligibility" in h_lower:
            primary = f"What is the eligibility criteria for {t_clean} at SDIT?"
            variations = [
                f"What qualifications and minimum marks are needed for admission into {t_clean}?",
                f"Can you tell me the entry requirements for {t_clean} at Shree Devi Institute of Technology?",
                f"Who is eligible to apply for {t_clean} at SDIT Mangalore?",
                f"What percentage in 12th / PUC is required for {t_clean} at SDIT?",
                f"SDIT {t_clean} eligibility criteria and admission prerequisites"
            ]
        elif "outcome" in h_lower or "objective" in h_lower:
            primary = f"What are the program outcomes (POs) and course objectives of {t_clean} at SDIT?"
            variations = [
                f"What skills and knowledge will students acquire after graduating from {t_clean}?",
                f"What are the graduate attributes and learning goals for {t_clean} students at SDIT?",
                f"Tell me about the program educational objectives of {t_clean}.",
                f"SDIT {t_clean} program outcomes and syllabus competencies"
            ]
        elif any(k in h_lower for k in ["subject", "curriculum", "course", "syllabus"]):
            primary = f"What subjects and curriculum are covered in {t_clean} at SDIT?"
            variations = [
                f"What core subjects and electives will I study in {t_clean} at Shree Devi Institute of Technology?",
                f"Can you give me an overview of the syllabus for {t_clean}?",
                f"What technical topics and course modules are taught in {t_clean}?",
                f"SDIT {t_clean} course syllabus, subjects, and curriculum"
            ]
        elif any(k in h_lower for k in ["lab", "facility", "infrastructure"]):
            primary = f"What laboratories and practical facilities are available for {t_clean} at SDIT?"
            variations = [
                f"Tell me about the computer centers, lab equipment, and software tools in {t_clean} at SDIT.",
                f"What hands-on practical lab facilities does the {t_clean} department provide?",
                f"Are the labs well-equipped for {t_clean} practicals at Shree Devi Institute of Technology?",
                f"SDIT {t_clean} laboratories, practical workshops, and lab infrastructure"
            ]
        elif any(k in h_lower for k in ["overview", "introduction", "about"]):
            primary = f"What is the overview and department details of {t_clean} at SDIT?"
            variations = [
                f"Tell me about the {t_clean} program at Shree Devi Institute of Technology.",
                f"Can you give me an introduction to {t_clean} at SDIT Mangalore?",
                f"What degree programs, specializations, and career pathways does {t_clean} offer?",
                f"Why should I choose {t_clean} at SDIT?",
                f"SDIT {t_clean} department overview, course details, and features"
            ]
        else:
            primary = f"What information is available regarding {h_clean} for {t_clean} at SDIT?"
            variations = [
                f"Tell me about {h_clean} in {t_clean} at Shree Devi Institute of Technology.",
                f"How does {h_clean} relate to the {t_clean} course at SDIT?",
                f"Can you provide details about {h_clean} for {t_clean}?",
                f"SDIT {t_clean} {h_clean} details"
            ]

    # 4. Admissions & Eligibility
    elif category == "Admissions & Eligibility":
        if "scholarship" in t_lower or "scholarship" in h_lower:
            primary = "What scholarships and financial assistance are available at SDIT?"
            variations = [
                "Does Shree Devi Institute of Technology offer merit-based scholarships?",
                "How can I apply for a scholarship at SDIT Mangalore?",
                "What are the criteria and eligibility for student scholarships at SDIT?",
                "Tell me about financial aid and fee concessions at SDIT.",
                "SDIT scholarship eligibility, application procedure, and benefits"
            ]
        elif "brochure" in t_lower:
            primary = f"Where can I find the information brochure for {t_clean} at SDIT?"
            variations = [
                f"How can I download the {t_clean} prospectus from Shree Devi Institute of Technology?",
                f"Tell me about the course brochure and admission handbook for {t_clean}.",
                f"SDIT {t_clean} brochure, prospectus, and application guide"
            ]
        else:
            primary = f"What are the admission requirements and eligibility criteria for {t_clean} at SDIT?"
            variations = [
                f"How can I apply for admission to {t_clean} at Shree Devi Institute of Technology?",
                f"What qualifying marks and certificates are needed for {t_clean} admission?",
                f"Tell me the complete admission procedure for {t_clean} at SDIT.",
                f"Who can apply for admission into {t_clean} at SDIT Mangalore?",
                f"SDIT {t_clean} admission procedure, eligibility rules, and application details"
            ]

    # 5. Placements & Careers
    elif category == "Placements & Careers":
        if any(k in t_lower or k in h_lower for k in ["compani", "recruit"]):
            primary = "Which companies recruit students and visit SDIT for campus placements?"
            variations = [
                "Who are the top recruiters and industry partners for Shree Devi Institute of Technology?",
                "What companies come for engineering, MCA, and MBA campus placements at SDIT?",
                "Can you name the major recruiting companies at SDIT Mangalore?",
                "Do companies like Infosys, IBM, and Tech Mahindra recruit from SDIT?",
                "SDIT campus recruitment company list and top placement partners"
            ]
        elif any(k in t_lower or k in h_lower for k in ["train", "progression"]):
            primary = "What placement training and career development programs are provided at SDIT?"
            variations = [
                "How does the Training & Placement Cell prepare students for job interviews at SDIT?",
                "Tell me about soft skills, aptitude training, and mock interviews for SDIT placements.",
                "What career development support does SDIT provide to final-year students?",
                "SDIT placement training programs, workshops, and interview coaching"
            ]
        elif "tpo" in t_lower or "tpo" in h_lower:
            primary = "What is the Training and Placement Officer (TPO) message at SDIT?"
            variations = [
                "What does the TPO say about placement opportunities and student readiness at SDIT?",
                "Read the placement cell head's address for Shree Devi Institute of Technology.",
                "SDIT TPO message, placement director thoughts, and corporate relations"
            ]
        else:
            primary = "What is the placement record and statistics at Shree Devi Institute of Technology?"
            variations = [
                "How are the campus placements at SDIT and what percentage of students get placed?",
                "Tell me about recent placement highlights, job offers, and salary packages at SDIT.",
                "What is the track record of engineering and management placements at SDIT?",
                "How many offer letters have been given to SDIT students in recent years?",
                "SDIT placement statistics, job offers, and placement percentage"
            ]

    # 6. Campus & Facilities
    elif category == "Campus & Facilities":
        if "sport" in t_lower or "sport" in h_lower:
            primary = "What sports facilities and athletic activities are available at SDIT?"
            variations = [
                "Does Shree Devi Institute of Technology support indoor and outdoor sports?",
                "Tell me about sporting competitions and grounds at SDIT Mangalore.",
                "What facilities exist for athletics, cricket, football, or indoor games at SDIT?",
                "SDIT sports amenities, tournaments, and team achievements"
            ]
        elif "club" in t_lower or "club" in h_lower:
            primary = "What student clubs and co-curricular activities exist at SDIT?"
            variations = [
                "Which cultural, technical, and sports clubs can I join at Shree Devi Institute of Technology?",
                "Tell me about student clubs and extracurricular life at SDIT.",
                "How can students get involved in college clubs and activities at SDIT?",
                "SDIT student clubs, cultural events, and technical forums"
            ]
        elif "location" in t_lower or "location" in h_lower:
            primary = "Where is Shree Devi Institute of Technology located and how do I reach it?"
            variations = [
                "What is the campus address and directions to SDIT in Kenjar, Mangalore?",
                "How far is SDIT from Mangalore International Airport and railway station?",
                "How can I travel to the SDIT campus by bus or road?",
                "SDIT location, route map, and distance from Mangalore airport"
            ]
        else:
            primary = "What campus infrastructure and student amenities are available at SDIT?"
            variations = [
                "Tell me about the classrooms, library, and campus facilities at SDIT.",
                "Does Shree Devi Institute of Technology provide hostel accommodation and transport?",
                "What are the main campus infrastructure highlights of SDIT Kenjar?",
                "SDIT campus facilities, library, hostel, and infrastructure"
            ]

    # 7. Contact & Support
    elif category == "Contact & Support":
        primary = "How can I contact Shree Devi Institute of Technology or visit the campus?"
        variations = [
            "What is the official phone number, email address, and campus location of SDIT?",
            "Where is SDIT campus located and what is the address in Kenjar, Mangalore?",
            "Can you give me the principal's office email and phone number for SDIT?",
            "What is the Trust Office address and phone number for Shree Devi Education Trust?",
            "SDIT contact details, phone number, email ID, and campus address"
        ]

    # 8. Committees & Governance
    elif "committee" in t_lower:
        if any(k in h_lower or k in c_lower for k in ["ragging"]):
            primary = "What is the Anti-Ragging policy, committee, and penalty rules at SDIT?"
            variations = [
                "Does SDIT have a strict anti-ragging committee and what are the UGC penalties?",
                "How does Shree Devi Institute of Technology prevent ragging on campus?",
                "Who can a student contact to report ragging at SDIT?",
                "SDIT anti-ragging regulations, committee members, and student safety guidelines"
            ]
        elif any(k in h_lower or k in c_lower for k in ["grievance", "complaint"]):
            primary = "What is the Grievance Redressal procedure for students at SDIT?"
            variations = [
                "How can a student file a complaint or grievance at Shree Devi Institute of Technology?",
                "What are the 4 steps involved in student grievance redressal at SDIT?",
                "Tell me about the Grievance Redressal Committee and resolution process at SDIT.",
                "SDIT grievance redressal committee steps and student complaint procedure"
            ]
        else:
            primary = f"What are the functions and committee details of {h_clean} at SDIT?"
            variations = [
                f"Tell me about the roles, responsibilities, and members of {h_clean} at SDIT.",
                f"What is the purpose and structure of the {h_clean} at Shree Devi Institute of Technology?",
                f"SDIT {h_clean} members, objectives, and responsibilities"
            ]

    # 9. Leadership & Administration
    elif any(k in t_lower for k in ["principal", "administrator", "vision", "affiliation", "strategic"]):
        if "vision" in t_lower or "mission" in t_lower:
            primary = "What are the Vision and Mission of Shree Devi Institute of Technology?"
            variations = [
                "Tell me about the core values and institutional goals of SDIT Mangalore.",
                "What is SDIT's mission regarding technical education and societal challenges?",
                "SDIT vision, mission statement, and core objectives"
            ]
        elif "affiliation" in t_lower or "recognition" in t_lower:
            primary = "What is the affiliation and accreditation status of SDIT?"
            variations = [
                "Is Shree Devi Institute of Technology approved by AICTE and affiliated with VTU?",
                "What recognitions, government approvals, and university affiliations does SDIT hold?",
                "SDIT VTU affiliation, AICTE approval, and accreditation details"
            ]
        elif "strategic" in t_lower:
            primary = "What is the Strategic Plan and future roadmap of SDIT?"
            variations = [
                "What are the long-term goals and strategic development plans for SDIT?",
                "Tell me about SDIT's institutional growth plan and academic benchmarks.",
                "SDIT strategic plan, vision roadmap, and development targets"
            ]
        else:
            primary = f"What is the message and institutional guidance shared by the {t_clean} of SDIT?"
            variations = [
                f"Tell me about the leadership address by the {t_clean} at Shree Devi Institute of Technology.",
                f"What guidance and objectives does the {t_clean} emphasize for SDIT students?",
                f"SDIT {t_clean} message, vision, and institutional guidance"
            ]

    # Fallback
    else:
        primary = f"What information is available about {h_clean} for {t_clean} at SDIT?"
        variations = [
            f"Tell me about {h_clean} at Shree Devi Institute of Technology.",
            f"Can you explain the details regarding {h_clean} for {t_clean} at SDIT?",
            f"What does SDIT state about {h_clean}?",
            f"SDIT {t_clean} {h_clean} details"
        ]

    return primary, variations


def build_qa_pairs(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate pragmatic Q&A pairs with multiple question forms suitable for FAQ chatbots,
    fine-tuning datasets, or direct system prompt injection.
    """
    qa_list: List[Dict[str, Any]] = []
    qa_id = 1

    for page in pages:
        title = page["title"]
        url = page["url"]
        category = page["category"]

        # 1. Contact Info Q&A
        if page["contacts"]["emails"] or page["contacts"]["phone_numbers"]:
            ans_parts = [f"Contact details for {title}:"]
            if page["contacts"]["phone_numbers"]:
                ans_parts.append(f"Phone numbers: {', '.join(page['contacts']['phone_numbers'])}")
            if page["contacts"]["emails"]:
                ans_parts.append(f"Email addresses: {', '.join(page['contacts']['emails'])}")
            ans_parts.append(f"Reference: {url}")

            primary_q = f"How can I contact the administration or department regarding {title} at SDIT?"
            variations = [
                f"What is the official phone number, email address, and campus location for {title}?",
                f"Where can I find contact information and reach out to {title} at Shree Devi Institute of Technology?",
                f"Give me the telephone numbers and email IDs for {title} at SDIT Mangalore.",
                f"{title} SDIT contact details, phone number, and email"
            ]

            qa_list.append({
                "id": f"sdit-qa-{qa_id:04d}",
                "question": primary_q,
                "question_variations": variations,
                "section": "Contact Information",
                "category": category,
                "answer": "\n".join(ans_parts),
                "url": url,
            })
            qa_id += 1

        # 2. Section-specific Q&A
        for section in page["sections"]:
            heading = section["heading"]

            lines = []
            for p in section["paragraphs"]:
                lines.append(p)
            for b_list in section["bullet_points"]:
                for item in b_list:
                    lines.append(f"- {item}")
            for tbl in section["tables"]:
                for row in tbl:
                    lines.append(" | ".join(row))

            sec_content = "\n".join(lines).strip()
            if len(sec_content) > 50:
                primary_q, variations = generate_multi_form_questions(
                    title=title,
                    heading=heading,
                    category=category,
                    content=sec_content,
                    url=url
                )

                qa_list.append({
                    "id": f"sdit-qa-{qa_id:04d}",
                    "question": primary_q,
                    "question_variations": variations,
                    "section": clean_heading_for_qa(heading),
                    "category": category,
                    "answer": f"{sec_content}\n\n(Source: {url})",
                    "url": url,
                })
                qa_id += 1

    return qa_list


def main():
    parser = argparse.ArgumentParser(
        description="Scrape and structure sdit.ac.in data for chatbot consumption in JSON format."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Directory where JSON files will be saved (default: data/)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent scraper threads (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Polite delay between requests in seconds (default: 0.2)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape (optional, default: scrape all)",
    )
    parser.add_argument(
        "--no-chunks",
        action="store_true",
        help="Disable generation of RAG chunk JSON file",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="Disable generation of Q&A dataset JSON file",
    )
    parser.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Rebuild Q&A and chunks from existing sdit_chatbot_knowledge.json without re-scraping",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    start_time = time.time()
    kb_filepath = os.path.join(args.output_dir, "sdit_chatbot_knowledge.json")

    if args.rebuild_only and os.path.exists(kb_filepath):
        logger.info(f"⚡ Rebuild-only mode: Loading existing knowledge base from {kb_filepath}...")
        with open(kb_filepath, "r", encoding="utf-8") as f:
            existing_kb = json.load(f)
        pages_data = existing_kb.get("pages", [])
        logger.info(f"Loaded {len(pages_data)} pages from local knowledge base.")
    else:
        scraper = SDITScraper(
            delay=args.delay,
            max_workers=args.workers,
            max_pages=args.max_pages,
        )

        try:
            pages_data = scraper.scrape_all()
        finally:
            scraper.close()

    elapsed = time.time() - start_time
    total_words = sum(p["word_count"] for p in pages_data)
    total_sections = sum(p["sections_count"] for p in pages_data)

    # 1. Save Master Knowledge Base JSON
    master_kb = {
        "metadata": {
            "institution_name": "Shree Devi Institute of Technology (SDIT)",
            "website": BASE_URL,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_pages": len(pages_data),
            "total_sections": total_sections,
            "total_word_count": total_words,
            "categories": sorted(list(set(p["category"] for p in pages_data))),
        },
        "pages": pages_data,
    }

    kb_filepath = os.path.join(args.output_dir, "sdit_chatbot_knowledge.json")
    with open(kb_filepath, "w", encoding="utf-8") as f:
        json.dump(master_kb, f, indent=2, ensure_ascii=False)
    logger.info(f"📁 Saved Master Knowledge Base -> {kb_filepath} ({len(pages_data)} pages)")

    # 2. Save RAG Chunks JSON
    if not args.no_chunks:
        chunks = build_rag_chunks(pages_data)
        chunks_filepath = os.path.join(args.output_dir, "sdit_chatbot_chunks.json")
        with open(chunks_filepath, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        logger.info(f"📁 Saved RAG Retrieval Chunks -> {chunks_filepath} ({len(chunks)} chunks)")

    # 3. Save Q&A Dataset JSON
    if not args.no_qa:
        qa_pairs = build_qa_pairs(pages_data)
        qa_filepath = os.path.join(args.output_dir, "sdit_chatbot_qa.json")
        with open(qa_filepath, "w", encoding="utf-8") as f:
            json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
        logger.info(f"📁 Saved Chatbot Q&A Dataset -> {qa_filepath} ({len(qa_pairs)} Q&A pairs)")

    print("\n" + "=" * 65)
    print("           SDIT CHATBOT DATA SCRAPING COMPLETED           ")
    print("=" * 65)
    print(f" • Execution Time    : {elapsed:.2f} seconds")
    print(f" • Pages Scraped     : {len(pages_data)}")
    print(f" • Total Sections    : {total_sections}")
    print(f" • Total Word Count  : {total_words:,} words")
    print(f" • Output Directory  : {os.path.abspath(args.output_dir)}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
