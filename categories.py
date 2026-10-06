"""File categories shared by the sorter and the report."""

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".ppt", ".pptx", ".csv", ".odt"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Code": {".py", ".js", ".html", ".css", ".json", ".java", ".cpp", ".c", ".sh", ".ipynb"},
}

OTHERS = "Others"

# Names of the folders the sorter creates in "type" mode.
CATEGORY_FOLDERS = set(CATEGORIES) | {OTHERS}


def get_category(extension: str) -> str:
    """Returns the category name for a file extension (for example ".JPG")."""
    extension = extension.lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return OTHERS
