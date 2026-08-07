import os
import config
from templates import index as home
from flask import Flask


app = Flask(__name__)
app.secret_key = "epub-twitter-demo"
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    return home.index()

@app.route("/render", methods=["POST"])
def render():
    return home.render()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=config.PORT_NUMBER)
