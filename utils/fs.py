import json
import shutil
from pathlib import Path


def ensureDir(directoryPath):
    Path(directoryPath).mkdir(parents=True, exist_ok=True)


def emptyDir(directoryPath):
    shutil.rmtree(directoryPath, ignore_errors=True)
    ensureDir(directoryPath)


def walkFiles(directoryPath):
    directory = Path(directoryPath)

    try:
        entries = list(directory.iterdir())
    except FileNotFoundError:
        return []

    results = []

    for entry in entries:
        if entry.is_dir():
            results.extend(walkFiles(entry))
        else:
            results.append(str(entry))

    return results


def readJson(filePath):
    with open(filePath, "r", encoding="utf8") as file:
        return json.load(file)

