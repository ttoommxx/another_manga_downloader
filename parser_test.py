import os
import requests

manga_name = "Pluto"

folder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MANGAS", manga_name)
os.makedirs(folder_path, exist_ok=True)

chapter_number = 1
while True:
    page_number = 1
    url_chapter = f"https://official.lowee.us/manga/Pluto/{chapter_number:04d}-{page_number:03d}.png"
    response = requests.get(url_chapter, stream=True, timeout=10)
    if response.status_code != 200:
        break

    chapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MANGAS", manga_name, f"{chapter_number:04d}")
    if os.path.exists(f"{chapter_path}.cbz"):
        continue
    os.makedirs(chapter_path, exist_ok=True)

    while True:
        response = requests.get(url_chapter, stream=True, timeout=10)
        if response.status_code != 200:
            break

        file_path = os.path.join(chapter_path, f"{page_number:03d}")
        if os.path.exists(file_path):
            continue
        # Open the file in binary write mode
        with open(file_path, "wb") as page:
            for chunk in response.iter_content(1024):
                page.write(chunk)

        page_number += 1
        url_chapter = f"https://official.lowee.us/manga/Pluto/{chapter_number:04d}-{page_number:03d}.png"
    
    chapter_number += 1