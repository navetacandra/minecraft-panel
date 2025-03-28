import mimetypes
import os
from server.config import SERVER_LOCATION
from server.server_manager import is_installed
from server.logger import socketio


def plugins_list():
    if not is_installed():
        return []
    plugin_dir = os.path.join(SERVER_LOCATION, "plugins")
    plugins = []
    for entry in os.scandir(plugin_dir):
        if entry.is_file(follow_symlinks=False) and entry.name.endswith(".jar"):
            plugins.append({ "name": entry.name, "path": entry.path.replace('\\', '/'), "mime": mimetypes.guess_type(entry.path) })
    return plugins


def plugin_find(path = ""):
    if not is_installed():
        raise Exception("Server not installed!")
    plugin_dir = os.path.join(SERVER_LOCATION, "plugins")
    for entry in os.scandir(plugin_dir):
        if entry.is_file(follow_symlinks=False) and entry.name.endswith(".jar") and entry.path.replace('\\', '/') == path:
            return { "name": entry.name, "path": entry.path.replace('\\', '/') }
    return None

def plugin_delete(path = ""):
    plugin = plugin_find(path)
    if plugin is not None:
        os.remove(plugin['path'])
        socketio.emit("plugins", plugins_list())
        return "", 200
    raise Exception("Plugin not found!")


def plugin_upload(files):
    if "plugin" not in files:
        raise Exception("No file uploaded!")
            
    file = files["plugin"]
    if file.filename == "":
        raise Exception("No file uploaded!")
    
    def check_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {"jar"}

    if file and check_file(file.filename):
        filepath = os.path.join(SERVER_LOCATION, "plugins", file.filename)
        file.save(filepath)
        socketio.emit("plugins", plugins_list())
        return "", 200
    else:
        raise Exception("Failed upload file!")