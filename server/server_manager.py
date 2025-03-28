import os
import re
import subprocess
import threading
import time
import psutil
from server.config import SERVER_LOCATION, load_server_settings
from server.logger import log_info, plain_log, socketio

server_process = None


def is_installed():
    settings = load_server_settings()
    return (
        not settings == {}
        and settings["executable"] is not None
        and os.path.exists(os.path.join(SERVER_LOCATION, settings["executable"]))
    )


def is_running():
    global server_process
    return server_process is not None


def handle_server_output():
    global server_process
    for line in iter(server_process.stdout.readline, b""):
        decoded_line = line.decode("utf-8").strip()
        decoded_line = re.sub(r"\x1b\[(\d+;?){,10}m", "", decoded_line)
        plain_log(decoded_line)

    for line in iter(server_process.stderr.readline, b""):
        decoded_line = line.decode("utf-8").strip()
        decoded_line = re.sub(r"\x1b\[(\d+;?){,10}m", "", decoded_line)
        plain_log(decoded_line)


def monitor_usage():
    global server_process
    try:
        ps_proc = psutil.Process(server_process.pid)
        while ps_proc.is_running():
            cpu_usage = ps_proc.cpu_percent(interval=1)
            mem_usage = ps_proc.memory_info().rss / (1024 * 1024)  # Convert to MB
            socketio.emit("usage", {"cpu": cpu_usage, "memory": mem_usage})
            time.sleep(1)
    except psutil.NoSuchProcess:
        log_info("Monitoring stopped. Process not found.")


def on_exit():
    global server_process
    server_process.wait()

    socketio.emit("status", False)
    server_process = None


def start_server():
    global server_process
    if is_running():
        raise Exception("Server already running!")

    log_info("Starting Server.")
    settings = load_server_settings()

    server_process = subprocess.Popen(
        [
            "java",
            f"-Xms{settings['min_memory']}",
            f"-Xmx{settings['max_memory']}",
            f"-XX:ActiveProcessorCount={settings['core_usage']}",
            "-jar",
            settings["executable"],
            "--nogui",
        ],
        cwd=SERVER_LOCATION,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    threading.Thread(target=on_exit).start()

    socketio.start_background_task(handle_server_output)
    socketio.start_background_task(monitor_usage)
    socketio.emit("status", True)


def stop_server():
    global server_process
    if not is_running():
        raise Exception("No running server!")
    log_info("Stopping server.")
    try:
        server_process.stdin.write(f"stop\n".encode("utf-8"))
        server_process.stdin.flush()
        server_process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        log_info("Server did not stop gracefully, terminating forcefully.", "WARNING")
        server_process.terminate()
        server_process.wait()


def restart_server():
    global server_process
    if not is_running():
        start_server()
    else:
        stop_server()
        start_server()


def run_command(command=""):
    global server_process
    if not is_running():
        raise Exception("No running server!")
    if server_process.stdin is None:
        raise Exception("Server process does not have stdin available!")
    if command is None or command == "":
        raise Exception("command is required!")
    server_process.stdin.write(f"{command}\n".encode("utf-8"))
    server_process.stdin.flush()
    log_info(f">{command}", "COMMAND")
