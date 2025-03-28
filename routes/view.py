import mimetypes
import os
from flask import Blueprint, abort, redirect, send_file
from server.config import SERVER_LOCATION
from server.server_manager import is_installed

view = Blueprint("view", __name__)
STATIC_PATH = os.path.join(SERVER_LOCATION, "..", "static")


def handle_file_cache(filepath):
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        abort(404)

    mimetype, _ = mimetypes.guess_type(filepath)
    response = send_file(filepath, mimetype=mimetype or "application/octet-stream")

    response.headers["Cache-Control"] = "public, max-age=31536000"
    return response


@view.route("/assets/<path:filename>", methods=["GET"])
def serve_assets(filename):
    return handle_file_cache(os.path.join(STATIC_PATH, "assets", filename))


@view.route("/", methods=["GET"])
def index():
    try:
        if is_installed():
            return handle_file_cache(os.path.join(STATIC_PATH, "index.html"))
        else:
            return handle_file_cache(os.path.join(STATIC_PATH, "install.html"))
    except Exception as e:
        print(e)
        return abort(500)


@view.route("/plugins", methods=["GET"])
def plugins():
    try:
        if is_installed():
            return handle_file_cache(os.path.join(STATIC_PATH, "plugins.html"))
        else:
            return redirect("/")
    except Exception as e:
        print(e)
        return abort(500)


@view.route("/file-manager", methods=["GET"])
def file_manager():
    try:
        if is_installed():
            return handle_file_cache(os.path.join(STATIC_PATH, "file_manager.html"))
        else:
            return redirect("/")
    except Exception as e:
        print(e)
        return abort(500)


@view.route("/editor", methods=["GET"])
def editor():
    try:
        if is_installed():
            return handle_file_cache(os.path.join(STATIC_PATH, "editor.html"))
        else:
            return redirect("/")
    except Exception as e:
        print(e)
        return abort(500)


@view.route("/server-setting", methods=["GET"])
def server_setting():
    try:
        if is_installed():
            return handle_file_cache(os.path.join(STATIC_PATH, "server_settings.html"))
        else:
            return redirect("/")
    except Exception as e:
        print(e)
        return abort(500)
