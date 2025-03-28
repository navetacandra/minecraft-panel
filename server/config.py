import os
import re


SERVER_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "minecraft_server")
)
SERVER_SETTING = os.path.abspath(os.path.join(SERVER_LOCATION, "..", "SERVER.settings"))
LOG_PATH = os.path.abspath(os.path.join(SERVER_LOCATION, "..", "log.txt"))

os.makedirs(SERVER_LOCATION, exist_ok=True)
if not os.path.exists(LOG_PATH):
    open(LOG_PATH, "w").close()


def get_value(str, pattern, default=None):
    _match = re.search(pattern, str)
    return _match.group(1) if _match else default


def load_server_settings():
    if not os.path.exists(SERVER_SETTING):
        return {}
    with open(SERVER_SETTING, "r") as f:
        settings = f.read()
    executable = get_value(settings, r"executable=(.+)", None)
    min_memory = get_value(settings, r"min-memory=(.+)", None)
    max_memory = get_value(settings, r"max-memory=(.+)", None)
    core_usage = get_value(settings, r"core-usage=(\d+)", None)
    playit_agent_secret_code = get_value(
        settings, r"playit-agent-secret-code=(.+)", None
    )

    return {
        "executable": executable,
        "min_memory": min_memory,
        "max_memory": max_memory,
        "core_usage": core_usage,
        "playit_agent_secret_code": playit_agent_secret_code,
    }


def update_server_settings(d):
    fkey = [
        "executable",
        "min-memory",
        "max-memory",
        "core-usage",
        "playit-agent-secret-code",
    ]
    jkey = [
        "executable",
        "min_memory",
        "max_memory",
        "core_usage",
        "playit_agent_secret_code",
    ]

    content = ''
    for i in range(0, len(jkey)):
        value = d[jkey[i]]
        content += f"{fkey[i]}={value if value is not None else ''}\n"
    
    with open(SERVER_SETTING, "w") as f:
        f.write(content)