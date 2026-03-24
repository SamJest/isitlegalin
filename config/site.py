from pathlib import Path


currentFile = Path(__file__).resolve()
currentDir = currentFile.parent

PYGEN_DIR = currentDir.parent
PROJECT_ROOT = str(PYGEN_DIR.parent)
ROOT_DIR = str(Path(PROJECT_ROOT) / "V2")
DATA_DIR = str(Path(ROOT_DIR) / "data")
RULES_DIR = str(Path(PYGEN_DIR) / "rules")
TEMPLATES_DIR = str(Path(PYGEN_DIR) / "templates")
ASSETS_DIR = str(Path(PYGEN_DIR) / "assets")
OUTPUT_DIR = str(Path(PYGEN_DIR) / "output")
LEGACY_DATA_DIR = str(Path(PROJECT_ROOT) / "data")

SITE_CONFIG = {
    "siteName": "Is It Legal In",
    "baseUrl": "https://isitlegalin.com",
    "locale": "en-GB",
}
