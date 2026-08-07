import os
import config
from templates import index as home, browse
from flask import Flask,request

app = Flask(__name__)
app.secret_key = "epub-twitter-demo"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

#region index
@app.route("/", methods=["GET"])
def index():
    filename = request.args.get("filename")
    return home.Home().index(filename)

@app.route("/upload", methods=["GET"])
def upload():
    return home.Home().upload()

@app.route("/upload-book", methods=["POST"])
def uploadbook():
    return home.Home().upload_book()

#region Browse
@app.route("/browse", methods=["GET"])
def book_search():
    return browse.Browse().index()
#endregion


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=config.PORT_NUMBER)
