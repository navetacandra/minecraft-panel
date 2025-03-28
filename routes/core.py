from flask import Flask
from routes.api import api
from routes.view import view

app = Flask(__name__, static_folder="static")

app.register_blueprint(api)
app.register_blueprint(view)