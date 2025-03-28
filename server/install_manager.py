import os
import re
import requests
from server.config import SERVER_LOCATION, SERVER_SETTING
from server.logger import log_info, socketio
from server.server_manager import is_installed


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
            f"executable={server_type}.jar\nserver-type={server_type}\nmin-memory=128M\nmax-memory=3G\ncore-usage=1\nplayit-agent-secret-code=\n"
        )

    def on_complete(_):
        socketio.emit("install")

    os.makedirs(SERVER_LOCATION, exist_ok=True)
    download_file(
        url, os.path.join(SERVER_LOCATION, f"{server_type}.jar"), callback=on_complete
    )
    with open(os.path.join(SERVER_LOCATION, "eula.txt"), "w") as f:
        f.write("eula=true")
