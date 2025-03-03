import os
import re
import requests
import subprocess
import threading
import mimetypes
from flask import Flask, abort, request, send_file, jsonify
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename


app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

SERVER_LOCATION = os.path.join(os.path.dirname(__file__), "minecraft_server")
SERVER_SETTING = os.path.join(SERVER_LOCATION, "..", "SERVER.settings")
LOG_PATH = os.path.join(SERVER_LOCATION, "..", "log.txt")
server_process = None

os.makedirs(SERVER_LOCATION, exist_ok=True)
if not os.path.exists(LOG_PATH):
    open(LOG_PATH, "w").close()


def download_static_assets():
    asset_path = os.path.join(os.path.dirname(__file__), "static", "assets")
    css_path = os.path.join(asset_path, "css")
    js_path = os.path.join(asset_path, "js")
    os.makedirs(asset_path, exist_ok=True)
    os.makedirs(css_path, exist_ok=True)
    os.makedirs(js_path, exist_ok=True)

    files = [
        os.path.join(css_path, "bootstrap.css"),
        os.path.join(css_path, "bootstrap.css.map"),
        os.path.join(js_path, "bootstrap.js"),
        os.path.join(js_path, "bootstrap.js.map"),
        os.path.join(js_path, "socket.io.js")
        os.path.join(js_path, "socket.io.js.map")
    ]
    urls = [
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.css",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.css.map",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.js",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.js.map",
        "https://cdn.socket.io/4.7.2/socket.io.js"
        "https://cdn.socket.io/4.7.2/socket.io.js.map"
    ]

    for i in range(len(files)):
        download_file(urls[i], files[i], log=False)


def log_info(message, log_type="SYSTEM"):
    msg = ""
    if not log_type == "NONE":
        msg = f"[{log_type}]: {message}\n"
    else:
        msg = f"{message}\n"

    with open(LOG_PATH, "a") as log:
        log.write(msg)

    if not log_type == "NONE":
        socketio.emit("log", msg)


def handle_file_cache(filepath):
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        abort(404)

    mimetype, _ = mimetypes.guess_type(filepath)
    response = send_file(filepath, mimetype=mimetype or "application/octet-stream")

    response.headers["Cache-Control"] = "public, max-age=31536000"
    return response


def download_file(url, filepath, log=True, callback=None):
    if log:
        log_info(f"Downloading {url}")
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(filepath, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        if log:
            log_info("Download finished")
        if callback:
            callback(filepath)
        return True
    else:
        if log:
            log_info("Download failed")
        return False


def is_installed():
    if not os.path.exists(SERVER_SETTING):
        return False
    with open(SERVER_SETTING, "r") as f:
        settings = f.read()
    executable = re.search(r"executable=(.+)", settings)
    return executable and os.path.exists(
        os.path.join(SERVER_LOCATION, executable.group(1))
    )


def get_versions(server_type="paper"):
    if server_type == "paper":
        response = requests.get("https://api.papermc.io/v2/projects/paper")
        return response.json().get("versions", [])[::-1]
    elif server_type == "purpur":
        response = requests.get("https://purpurmc.org/download/purpur/")
        html = response.text
        return re.findall(r'option value="([^"]+)"', html)
    return []


def get_jar_download_url(server_type, version):
    if server_type == "paper":
        builds = requests.get(
            f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
        ).json()
        latest_build = builds["builds"][-1]
        return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build['build']}/downloads/{latest_build['downloads']['application']['name']}"
    elif server_type == "purpur":
        html = requests.get(f"https://purpurmc.org/download/purpur/{version}").text
        match = re.search(
            r'href="(https://api.purpurmc.org/v2/purpur/[^/]+/[^/]+/download)"', html
        )
        return match.group(1) if match else ""
    return ""


def install_server(server_type="paper", version=""):
    if is_installed():
        raise Exception("Server already installed!")
    version = version or get_versions(server_type)[0]
    url = get_jar_download_url(server_type, version)
    if not url:
        raise Exception("Failed to get jar file!")
    log_info("Preparing to install server")
    with open(SERVER_SETTING, "w") as f:
        f.write(
            f"executable={server_type}.jar\nserver-type={server_type}\nmin-memory=128M\nmax-memory=3G\ncore-usage=1\n"
        )
    def on_complete(_):
        socketio.emit('install')
    download_file(
            url, 
            os.path.join(SERVER_LOCATION, f"{server_type}.jar"), 
            callback=on_complete
        )
    with open(os.path.join(SERVER_LOCATION, "eula.txt"), "w") as f:
        f.write("eula=true")


def handle_server_output():
    for line in iter(server_process.stdout.readline, b""):
        decoded_line = line.decode("utf-8").strip()
        decoded_line = re.sub(r"\x1b\[(\d+;?){,10}m", "", decoded_line)
        log_info(decoded_line, log_type="NONE")
        socketio.emit("log", f"{decoded_line}\n")

    for line in iter(server_process.stderr.readline, b""):
        decoded_line = line.decode("utf-8").strip()
        decoded_line = re.sub(r"\x1b\[(\d+;?){,10}m", "", decoded_line)
        log_info(decoded_line, log_type="NONE")
        socketio.emit("log", f"{decoded_line}\n")


def on_server_exit():
    global server_process
    server_process.wait()
    socketio.emit("status", False)
    server_process = None


def start_server():
    global server_process
    if not is_installed():
        raise Exception("Server not installed!")
    if server_process:
        raise Exception("Server already running!")
    with open(SERVER_SETTING, "r") as f:
        settings = f.read()
    executable = re.search(r"executable=(.+)", settings).group(1)
    min_memory = re.search(r"min-memory=(.+)", settings).group(1)
    max_memory = re.search(r"max-memory=(.+)", settings).group(1)
    core_usage = re.search(r"core-usage=(\d+)", settings).group(1)
    log_info("Starting server...")
    server_process = subprocess.Popen(
        [
            "java",
            f"-Xms{min_memory}",
            f"-Xmx{max_memory}",
            f"-XX:ActiveProcessorCount={core_usage}",
            "-jar",
            executable,
            "--nogui",
        ],
        cwd=SERVER_LOCATION,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    exit_thread = threading.Thread(target=on_server_exit)
    exit_thread.start()

    socketio.start_background_task(handle_server_output)
    socketio.emit("status", True)


def stop_server():
    global server_process
    if not server_process:
        raise Exception("No running server!")
    log_info("Stopping server...")
    try:
        server_process.stdin.write(f"stop\n".encode("utf-8"))
        server_process.stdin.flush()
        server_process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        log_info("Server did not stop gracefully, terminating forcefully.", "WARNING")
        server_process.terminate()
        server_process.wait()


def restart_server():
    if not server_process:
        start_server()
    else:
        stop_server()
        start_server()


def run_command(cmd):
    if not server_process:
        raise Exception("No running server!")
    if server_process.stdin is None:
        raise Exception("Server process does not have stdin available!")
    server_process.stdin.write(f"{cmd}\n".encode("utf-8"))
    server_process.stdin.flush()
    log_info(f"> {cmd}", "COMMAND")


@app.route("/version/<server>", methods=["GET"])
def version(server):
    return jsonify({"status": "OK", "versions": get_versions(server)})


@app.route("/install/<server>/<version>", methods=["GET"])
def install(server, version):
    try:
        install_server(server, version)
        return jsonify({"status": "OK"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/start", methods=["GET"])
def start():
    try:
        start_server()
        return jsonify({"status": "OK"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/stop", methods=["GET"])
def stop():
    try:
        stop_server()
        return jsonify({"status": "OK"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/restart", methods=["GET"])
def restart():
    try:
        restart_server()
        return jsonify({"status": "OK"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/clear-log", methods=["GET"])
def clear_log():
    try:
        with open(LOG_PATH, "w") as log:
            log.write("")
        socketio.emit("clear", True)
        log_info("Log file cleared", log_type="SYSTEM")
        return jsonify({"status": "OK", "message": "Log file cleared"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route("/run-command", methods=["GET"])
def run_command_endpoint():
    try:
        command = request.args.get("command")
        if not command:
            return (
                jsonify(
                    {
                        "status": "ERROR",
                        "code": 400,
                        "message": "command can't be empty!",
                    }
                ),
                400,
            )

        run_command(command)
        return jsonify({"status": "OK", "code": 200})
    except Exception as err:
        return jsonify({"status": "ERROR", "code": 500, "message": str(err)}), 500


@app.route("/")
def serve_index():
    if is_installed():
        return handle_file_cache("static/index.html")
    else:
        return handle_file_cache("static/install.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return handle_file_cache(os.path.join("static", "assets", filename))


@socketio.on("connect")
def connect():
    is_running = server_process is not None
    socketio.emit("status", is_running)

    try:
        with open(LOG_PATH, "r") as log_file:
            log_contents = log_file.read()
            socketio.emit("log", log_contents)
    except Exception as e:
        socketio.emit("log", f"Error reading log file: {str(e)}")


if __name__ == "__main__":
    download_static_assets()

    socketio.run(app, host="0.0.0.0", port=3000)
