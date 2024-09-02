"""collection of manga websites and their functions"""

##### add to here
from .mangalife import Mangalife
from .batoto import Batoto

mangas = (Mangalife, Batoto)
#####


def create_manga_dict(timeout: int) -> dict:
    """return a list of mangas instances"""
    return {class_manga.name: class_manga(timeout) for class_manga in mangas}


def get_manga_website(url: str) -> str:
    """identify manga website from the url"""
    for class_manga in mangas:
        if url.startswith(class_manga.page):
            return class_manga.name
    return ""
