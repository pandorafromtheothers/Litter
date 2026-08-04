import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from flask import Flask, flash, redirect, render_template, request, session, url_for
import json
from werkzeug.utils import secure_filename

try:
    from ebooklib import epub
except ImportError:  # pragma: no cover
    epub = None

app = Flask(__name__)
app.secret_key = "epub-twitter-demo"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["CACHE_DIR"] = os.path.join(app.config["UPLOAD_FOLDER"], "cache")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["CACHE_DIR"], exist_ok=True)
perpage = 20


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", "\n", text)
    return text.strip()


def split_paragraphs(text: str):
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


def build_post(paragraph: str, index: int):
    return {
        "id": index,
        "text": paragraph,
    }


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return clean_text(soup.get_text(" "))


def normalize_href(href: str) -> str:
    if not href:
        return ""
    href = href.split("#", 1)[0].strip()
    if href.startswith("./"):
        href = href[2:]
    return href.strip("/")


def flatten_toc(toc):
    entries = []
    for item in toc:
        if hasattr(item, "title") and hasattr(item, "href"):
            entries.append((item.title or "Untitled chapter", item.href or ""))
            children = getattr(item, "children", None)
            if children is not None:
                entries.extend(flatten_toc(children))
        elif isinstance(item, tuple) and len(item) == 3:
            title, href, children = item
            entries.append((title or "Untitled chapter", href or ""))
            entries.extend(flatten_toc(children))
        elif isinstance(item, list):
            entries.extend(flatten_toc(item))
    return entries


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


def parse_epub(path: str):
    if epub is None:
        raise RuntimeError("The ebooklib package is not installed.")

    book = epub.read_epub(path)
    title = ""
    author = ""

    meta = book.get_metadata("DC", "title")
    if meta:
        title = meta[0][0]

    author_meta = book.get_metadata("DC", "creator")
    if author_meta:
        author = author_meta[0][0]

    posts = []
    item_starts = []

    for item in get_ordered_text_items(book):
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
        start_index = len(posts)
        paragraphs = split_paragraphs(extract_text_from_html(text))
        for paragraph in paragraphs:
            if len(paragraph.split()) >= 3:
                posts.append(build_post(paragraph, len(posts)))

        item_starts.append((item_href, start_index))

    chapters = build_chapters(book, item_starts, len(posts))
    return title, author, posts, chapters


def parse_mobi_with_calibre(path: str):
    calibre = shutil.which("ebook-convert")
    if not calibre:
        raise RuntimeError(
            "MOBI support needs the Calibre command-line tool. Install Calibre and ensure 'ebook-convert' is on your PATH."
        )

    temp_dir = tempfile.mkdtemp(dir=app.config["UPLOAD_FOLDER"])
    html_path = os.path.join(temp_dir, "converted.html")
    result = subprocess.run([calibre, path, html_path], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Calibre conversion failed: {result.stderr or result.stdout}")

    text = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    paragraphs = split_paragraphs(clean_text(text))
    return "Converted book", "Calibre", paragraphs


def parse_book(path: str):
    extension = Path(path).suffix.lower()
    if extension == ".epub":
        title, author, posts, chapters = parse_epub(path)
    elif extension == ".mobi":
        title, author, paragraphs = parse_mobi_with_calibre(path)
        cleaned_paragraphs = [p for p in paragraphs if len(p.split()) >= 3]
        posts = [build_post(p, index) for index, p in enumerate(cleaned_paragraphs)]
        chapters = [{"id": 0, "title": "All chapters", "start": 0, "end": len(posts)}]
    else:
        raise RuntimeError("Only .epub and .mobi files are supported.")

    return title or "Untitled book", author or "Unknown author", posts, chapters


def paginate_posts(posts, page: int, per_page: int = perpage):
    page = max(1, page)
    start = (page - 1) * per_page
    end = start + per_page
    return posts[start:end], len(posts), page


def cache_key_for(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._") or "book"


def save_posts_to_cache(filename: str, title: str, author: str, posts, chapters):
    cache_file = os.path.join(app.config["CACHE_DIR"], f"{cache_key_for(filename)}.json")
    payload = {"title": title, "author": author, "posts": posts, "chapters": chapters}
    with open(cache_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def load_posts_from_cache(filename: str):
    cache_file = os.path.join(app.config["CACHE_DIR"], f"{cache_key_for(filename)}.json")
    if not os.path.exists(cache_file):
        return None
    with open(cache_file, "r", encoding="utf-8") as handle:
        return json.load(handle)


@app.route("/", methods=["GET", "POST"])
def index():
    page = request.args.get("page", 1, type=int)
    chapter_id = request.args.get("chapter", 0, type=int)

    if request.method == "POST":
        uploaded_file = request.files.get("book")
        if not uploaded_file or uploaded_file.filename == "":
            flash("Choose a file to upload.")
            return redirect(url_for("index"))

        filename = secure_filename(uploaded_file.filename)
        destination = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        uploaded_file.save(destination)

        try:
            title, author, posts, chapters = parse_book(destination)
        except Exception as exc:  # pragma: no cover - user-facing path
            flash(str(exc))
            return redirect(url_for("index"))

        save_posts_to_cache(filename, title, author, posts, chapters)
        session["filename"] = filename
        selected_chapter = next((chapter for chapter in chapters if chapter["id"] == chapter_id), chapters[0])
        chapter_posts = posts[selected_chapter["start"]:selected_chapter["end"]]
        page_posts, total_posts, current_page = paginate_posts(chapter_posts, page)
        return render_template(
            "index.html",
            title=title,
            author=author,
            posts=page_posts,
            chapters=chapters,
            selected_chapter_id=selected_chapter["id"],
            uploaded_name=filename,
            total_posts=total_posts,
            current_page=current_page,
            per_page=perpage,
        )

    filename = session.get("filename", "")
    if filename:
        cached = load_posts_from_cache(filename)
        if cached:
            posts = cached.get("posts", [])
            chapters = cached.get("chapters", [{"id": 0, "title": "All chapters", "start": 0, "end": len(posts)}])
            selected_chapter = next((chapter for chapter in chapters if chapter["id"] == chapter_id), chapters[0])
            chapter_posts = posts[selected_chapter["start"]:selected_chapter["end"]]
            page_posts, total_posts, current_page = paginate_posts(chapter_posts, page)
            return render_template(
                "index.html",
                title=cached.get("title", ""),
                author=cached.get("author", ""),
                posts=page_posts,
                chapters=chapters,
                selected_chapter_id=selected_chapter["id"],
                uploaded_name=filename,
                total_posts=total_posts,
                current_page=current_page,
                per_page=perpage,
            )

    return render_template("index.html", title="Litter", author="", posts=[], uploaded_name="", total_posts=0, current_page=1, per_page=perpage)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
