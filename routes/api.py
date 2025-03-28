from flask import Blueprint, jsonify, request
from server.config import SERVER_LOCATION, load_server_settings, update_server_settings
from server.file_manager import delete_file, get_file_content, list_server_dir, write_file
from server.install_manager import get_versions, install_server
from server.logger import clear_log
from server.playit_manager import playit_disable, playit_enable
from server.plugin_manager import plugin_delete, plugin_upload
from server.server_manager import run_command, start_server, stop_server, restart_server

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/<server>/versions", methods=["GET"])
def server_versions_endpoint(server):
    return jsonify({"status": "OK", "versions": get_versions(server)})


@api.route("/install/<server>/<version>", methods=["GET"])
def install_server_endpoint(server, version):
    try:
        install_server(server, version)
        return jsonify({"status": "OK"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/clear_log", methods=["GET"])
def clear_log_endpoint():
    try:
        clear_log()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/server/start", methods=["GET"])
def start_server_endpoint():
    try:
        start_server()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/server/stop", methods=["GET"])
def stop_server_endpoint():
    try:
        stop_server()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/server/restart", methods=["GET"])
def restart_server_endpoint():
    try:
        restart_server()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/server/execute", methods=["GET"])
def run_command_endpoint():
    try:
        command = request.args.get("command")
        run_command(command)
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/plugin", methods=["DELETE", "POST"])
def plugin_endpoint():
    try:
        if request.method == "DELETE":
            return plugin_delete(request.args.get("plugin"))
        if request.method == "POST":
            return plugin_upload(request.files)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/playit/enable", methods=["GET"])
def playit_enable_endpoint():
    try:
        playit_enable()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/playit/disable", methods=["GET"])
def playit_disable_endpoint():
    try:
        playit_disable()
        return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/dir", methods=["GET"])
def list_dir_endpoint():
    try:
        path = request.args.get("path")
        path = path if path is not None else ''
        items = list_server_dir(path, base=SERVER_LOCATION)
        return jsonify({"status": "OK", "items": items}), 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/file", methods=["GET", "POST", "DELETE"])
def file_content_endpoint():
    try:
        path = request.args.get("path")
        path = path if path is not None else ''
        if request.method == "GET":
            d = get_file_content(path, base=SERVER_LOCATION)
            return (
                jsonify({"status": "OK", "content": d["content"], "path": d["path"]}),
                200,
            )
        elif request.method == "POST":
            json = request.json
            content = json["content"]
            write_file(path, content, base=SERVER_LOCATION)
            return "", 200
        elif request.method == "DELETE":
            delete_file(path, base=SERVER_LOCATION)
            return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@api.route("/server-setting", methods=["GET", "POST"])
def server_setting_endpoint():
    try:
        if request.method == "GET":
            settings = load_server_settings()
            return jsonify({"status": "OK", "settings": settings}), 200
        elif request.method == "POST":
            json = request.json
            update_server_settings(json)
            return "", 200
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500
