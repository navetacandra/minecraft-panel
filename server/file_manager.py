import os

from server.config import SERVER_LOCATION


def list_server_dir(path='', base=""):
    path = os.path.join(base, *path.split('/'))
    if not os.path.exists(path):
        raise Exception("Path not exists!")

    if not os.path.isdir(path):
        raise Exception("Path is not directory!")

    items = []
    for entry in os.scandir(path):
        items.append(
            {
                "path": entry.path.replace(SERVER_LOCATION, "", 1).replace("\\", "/"),
                "name": entry.name,
                "is_file": entry.is_file(follow_symlinks=False),
            }
        )
    return sorted(items, key=lambda d: d["is_file"])


def get_file_content(path='', base=""):
    path = os.path.join(base, *path.split('/'))
    if not os.path.exists(path):
        raise Exception("Path not exists!")

    if not os.path.isfile(path):
        raise Exception("Path is not file!")

    with open(path, "r") as file:
        content = file.read()
        return {"content": content, "path": path}


def write_file(path='', content='', base=""):
    path = os.path.join(base, *path.split('/'))
    if not os.path.exists(path):
        raise Exception("Path not exists!")

    if not os.path.isfile(path):
        raise Exception("Path is not file!")

    with open(path, "w") as file:
        file.write(content)


def delete_file(path='', base=""):
    path = os.path.join(base, *path.split('/'))
    if not os.path.exists(path):
        raise Exception("Path not exists!")

    if not os.path.isfile(path):
        raise Exception("Path is not file!")

    os.remove(path)