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
    return home.index(filename)

@app.route("/upload", methods=["POST"])
def upload():
    return home.upload()

#region Browse
@app.route("/browse", methods=["GET", "POST"])
def book_search():
    return browse.index()
#endregion


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=config.PORT_NUMBER)
