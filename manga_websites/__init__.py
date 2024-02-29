"""collection of manga websites and their functions"""
from .mangalife import Mangalife
from .batoto import Batoto

get_manga = {"mangalife": Mangalife(), "batoto": Batoto()}


def get_manga_website(url: str) -> str:
    """identify manga website from the url"""
    if url.startswith("https://www.manga4life.com/manga/"):
        return "mangalife"
    if url.startswith("https://bato.to/series/"):
        return "batoto"
    return ""
