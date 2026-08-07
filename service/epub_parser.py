import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
try:
    from ebooklib import epub
except ImportError:  # pragma: no cover
    epub = None

class Book:
    def __init__(self, isMobi = False):
        self.title = "Litter"
        self.author = "unknown"
        self.posts = []
        self.chapters = []
        self.selected_chapter = {"id": 0}
        self.total_posts= 0
        self.current_page = 1
        self.page_posts = []
        self.isMobi = isMobi
        
    def get_epub_book(self, path: str):
        if epub is None:
            raise RuntimeError("The ebooklib package is not installed.")

        item_starts = []
        book_epub = epub.read_epub(path)

        meta = book_epub.get_metadata("DC", "title")
        if meta:
            self.title = meta[0][0]

        author_meta = book_epub.get_metadata("DC", "creator")
        if author_meta:
            self.author = author_meta[0][0]


        for item in get_ordered_text_items(book_epub):
            content = item.get_content()
            if not content:
                continue

            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="ignore")
            elif isinstance(content, str):
                text = content
            else:
                continue

            item_href = normalize_href(getattr(item, "get_name", lambda: "")() or getattr(item, "href", "") or "")
            start_index = len(self.posts)
            paragraphs = get_paragraphs(extract_text_from_html(text, self.isMobi))
            for paragraph in paragraphs:
                if len(paragraph.split()) >= 3:
                    self.posts.append(build_post(paragraph, len(self.posts)))

            item_starts.append((item_href, start_index))

        self.chapters = build_chapters(book_epub, item_starts, len(self.posts))
        return self
    def convert_mobi_to_epub(self, path: str):
        calibre = shutil.which("ebook-convert")
        if not calibre:
            raise RuntimeError(
                "MOBI support needs the Calibre command-line tool. Install Calibre and ensure 'ebook-convert' is on your PATH."
            )
        epub_path = path.replace(".mobi", ".epub")
        process_result = subprocess.run([calibre, path, epub_path], capture_output=True, text=True)

        if process_result.returncode != 0:
            raise RuntimeError(f"Calibre conversion failed: {process_result.stderr or process_result.stdout}")

        return epub_path
    
#region HTML cleaner
def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", "\n", text)
    return text.strip()

def extract_text_from_html(html: str, isMobi) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if(isMobi):
        block_tags = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"}

        blocks = []
        for tag in soup.find_all(block_tags):
            if tag.find_parent(block_tags):
                continue

            text = clean_text(tag.get_text(" ", strip=True))
            if text:
                blocks.append(text)

        if blocks:
            return "\n\n".join(blocks)

    return clean_text(soup.get_text(" "))


def normalize_href(href: str) -> str:
    if not href:
        return ""
    href = href.split("#", 1)[0].strip()
    if href.startswith("./"):
        href = href[2:]
    return href.strip("/")

def get_paragraphs(text: str):
    cleaned = clean_text(text)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", cleaned) if block.strip()]
    paragraphs = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            paragraphs.extend(lines)
    if not paragraphs:
        paragraphs = [p.strip() for p in cleaned.splitlines() if p.strip()]
    return paragraphs
#endregion



def get_ordered_text_items(book):
    spine = getattr(book, "spine", None)
    items = []
    if isinstance(spine, list):
        for entry in spine:
            if isinstance(entry, tuple) and len(entry) >= 2:
                item_id = entry[1]
                item = getattr(book, "get_item_with_id", lambda x: None)(item_id)
                if item is not None and is_text_document(item):
                    items.append(item)
    if items:
        return items
    return [item for item in book.get_items() if is_text_document(item)]

def build_post(paragraph: str, index: int):
    return {
        "id": index,
        "text": paragraph,
    }

def flatten_toc(toc):
    entries = []
    for item in toc:
        if hasattr(item, "title") and hasattr(item, "href"):
            entries.append((item.title or "Untitled chapter", item.href or ""))
            children = getattr(item, "children", None)
            if children is not None:
                entries.extend(flatten_toc(children))
        elif isinstance(item, tuple) and len(item) > 1:
            title = item[0].title
            href = item[0].href
            entries.append((title or "Untitled chapter", href or ""))
            entries.extend(flatten_toc(item[1]))
        elif isinstance(item, list):
            entries.extend(flatten_toc(item))
    return entries





def get_chapter_start(item_starts, href: str):
    normalized = normalize_href(href)
    if not normalized:
        return None

    lookup = {item_href: start for item_href, start in item_starts}
    if normalized in lookup:
        return lookup[normalized]

    target_basename = os.path.basename(normalized)
    for item_href, start in item_starts:
        if os.path.basename(item_href) == target_basename:
            return start

    for item_href, start in item_starts:
        if item_href.endswith(normalized) or normalized.endswith(item_href):
            return start

    return None


def build_chapters(book, item_starts, total_posts):
    entries = flatten_toc(getattr(book, "toc", []))
    chapters = []
    for title, href in entries:
        start = get_chapter_start(item_starts, href)
        if start is None:
            continue
        chapters.append({"title": title.strip() or "Untitled chapter", "start": start})

    chapters.sort(key=lambda entry: entry["start"])
    final_chapters = [{"id": 0, "title": "All chapters", "start": 0, "end": total_posts}]
    seen_starts = {0}
    for entry in chapters:
        if entry["start"] in seen_starts:
            continue
        seen_starts.add(entry["start"])
        final_chapters.append({"id": len(final_chapters), "title": entry["title"], "start": entry["start"], "end": total_posts})

    for index in range(1, len(final_chapters)):
        current = final_chapters[index]
        next_start = final_chapters[index + 1]["start"] if index + 1 < len(final_chapters) else total_posts
        current["end"] = next_start

    return final_chapters


def is_text_document(item) -> bool:
    content = item.get_content()
    if not content:
        return False

    name = (item.get_name() or "").lower()
    if name.endswith((".xhtml", ".html", ".xml")):
        return True

    get_media_type = getattr(item, "get_media_type", None)
    if callable(get_media_type):
        media_type = str(get_media_type()).lower()
        return media_type in {"application/xhtml+xml", "text/html", "application/xml"}

    return False








def parse_book(path: str):
    extension = Path(path).suffix.lower()
    book = Book(os.path.basename(path).lower().endswith(".mobi"))
    match extension:
        case ".epub":
            path = path;
        case ".mobi":
            path = book.convert_mobi_to_epub(path)

        case _:
            raise RuntimeError("Only .epub and .mobi files are supported.")

    book = book.get_epub_book(path)
    return book