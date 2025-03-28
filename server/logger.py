import datetime
from server.config import LOG_PATH
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")

def plain_log(message):
    with open(LOG_PATH, "a") as log:
        log.write(f'{message}\n')
    socketio.emit("log", f'{message}\n')
        
def log_info(message, log_type="SYSTEM"):
    now = datetime.datetime.now()
    timestamp = now.strftime("%H:%M:%S")
    msg = f"[{timestamp} {log_type}]: {message}\n"

    with open(LOG_PATH, "a") as log:
        log.write(msg)
    socketio.emit("log", msg)

def clear_log():
    with open(LOG_PATH, "w") as log:
        log.write('')
    socketio.emit("clear")
    log_info("Log file cleared.")
    