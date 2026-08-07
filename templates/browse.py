import os
import Litter
from service import navigation

#region Views
class Browse:
    def __init__(self):
        navigation.set_active("Explore")

    def index(self):
        result = []
        imported_books = os.listdir(Litter.app.config["UPLOAD_FOLDER"]);
        for book in imported_books:
            result.append(str(book).replace(".json", ""))

        return navigation.render("browse.html", books=result)
#endregion