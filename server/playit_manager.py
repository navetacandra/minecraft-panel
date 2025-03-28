import subprocess
import threading
from server.config import SERVER_LOCATION, load_server_settings
from server.logger import log_info, socketio

playit_process = None


def is_playit_running():
    return playit_process is not None


def on_exit():
    global playit_process
    playit_process.wait()
    socketio.emit("playit", False)
    playit_process = None


def playit_enable():
    global playit_process
    if playit_process is not None:
        raise Exception("Playit already running!")

    server_config = load_server_settings()
    playit_key = server_config["playit_agent_secret_code"]
    if playit_key is None:
        log_info("Playit secret key not present!")
        raise Exception("Playit secret key not present!")

    playit_process = subprocess.Popen(
        [
            "playit",
            "--secret",
            playit_key,
        ],
        cwd=SERVER_LOCATION,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    log_info("Starting playit...")
    exit_thread = threading.Thread(target=on_exit)
    exit_thread.start()

    socketio.emit("playit", True)


def playit_disable():
    global playit_process

    if playit_process is None:
        raise Exception("No running playit!")
    log_info("Stopping playit...")
    playit_process.terminate()
