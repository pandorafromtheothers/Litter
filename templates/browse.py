import os
import Litter
from flask import render_template

def index():
    result = []
    imported_books = os.listdir(Litter.app.config["UPLOAD_FOLDER"]);
    for book in imported_books:
        result.append(str(book).replace(".json", ""))

    return render_template("browse.html", books=result)