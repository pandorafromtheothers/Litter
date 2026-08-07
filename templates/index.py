import os
import re
import json
import config
from service import epub_parser
from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
import Litter

def index(filename):
    page = request.args.get("page", 1, type=int)
    chapter_id = request.args.get("chapter", 0, type=int)
    book = epub_parser.Book()

    if filename is None:
        filename = session.get("filename", "")

    if filename:
        cached = load_posts_from_cache(filename)
        session["filename"] = filename
        if cached:
            book.author = cached.get("author", "")
            book.title=cached.get("title", "")
            book.posts = cached.get("posts", [])
            book.chapters = cached.get("chapters", [{"id": 0, "title": "All chapters", "start": 0, "end": len(book.posts)}])
            book.selected_chapter = next((chapter for chapter in book.chapters if chapter["id"] == chapter_id), book.chapters[0])
            book.chapter_posts = book.posts[book.selected_chapter["start"]:book.selected_chapter["end"]]
            book.page_posts, book.total_posts, book.current_page = paginate_posts(book.chapter_posts, page)

    return render_template(
        "index.html",
        title=book.title,
        author=book.author,
        posts=book.page_posts,
        chapters=book.chapters,
        selected_chapter_id=book.selected_chapter["id"],
        total_posts=book.total_posts,
        current_page=book.current_page,
        per_page = config.POST_PER_PAGE)

def upload():
    if request.method == "POST":
        uploaded_file = request.files.get("book")
        if not uploaded_file or uploaded_file.filename == "":
            flash("Choose a file to upload.")
            return redirect(url_for("index"))

        filename = secure_filename(uploaded_file.filename)
        destination = os.path.join(Litter.app.config["UPLOAD_FOLDER"], filename)
        uploaded_file.save(destination)

        try:
            book = epub_parser.parse_book(destination)
        except Exception as exc:  # pragma: no cover - user-facing path
            flash(str(exc))
            return redirect(url_for("index"))

        save_posts_to_cache(filename, book)
        session["filename"] = filename

        request.files = None

    return redirect(url_for("index"))



def paginate_posts(posts, page: int):
    page = max(1, page)
    start = (page - 1) * config.POST_PER_PAGE
    end = start + config.POST_PER_PAGE
    return posts[start:end], len(posts), page


def cache_key_for(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._") or "book"


def save_posts_to_cache(filename: str, book: epub_parser.Book):
    cache_file = os.path.join(Litter.app.config["UPLOAD_FOLDER"], f"{cache_key_for(filename)}.json")
    payload = {"title": book.title, "author": book.author, "posts": book.posts, "chapters": book.chapters}
    with open(cache_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def load_posts_from_cache(filename: str):
    cache_file = os.path.join(Litter.app.config["UPLOAD_FOLDER"], f"{cache_key_for(filename)}.json")
    if not os.path.exists(cache_file):
        return None
    with open(cache_file, "r", encoding="utf-8") as handle:
        return json.load(handle)