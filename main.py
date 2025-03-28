from routes.core import app
from server.config import LOG_PATH
from server.logger import socketio
from server.playit_manager import is_playit_running
from server.plugin_manager import plugins_list
from server.server_manager import is_running


@socketio.on('connect')
def on_connect():
    socketio.emit("status", is_running())
    socketio.emit("playit", is_playit_running())
    socketio.emit("plugins", plugins_list())
    
    try:
        with open(LOG_PATH, "r") as log_file:
            log_contents = log_file.read()
            socketio.emit("log", log_contents)
    except Exception as e:
        socketio.emit("log", f"Error reading log file: {str(e)}")


if __name__ == "__main__":
    socketio.init_app(app)
    socketio.run(app, host="0.0.0.0", port=3001)
