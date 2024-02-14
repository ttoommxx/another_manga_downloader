""" necessary modules """
import os
import sys
import argparse
import multiprocessing
import requests
import re
import ast
from zipfile import ZipFile


parser = argparse.ArgumentParser(prog="mangalife_downloader", description="download manga from mangalife")
parser.add_argument("name")
ARGS = parser.parse_args() # args.picker contains the modality


def printer(manga: str, printing_queue: multiprocessing.Manager().Queue, number_chapters: int) -> None:
    """ function that updates the count of the executed chapters """
    failed = []
    for i in range(1, number_chapters+1):
        token = printing_queue.get()
        if token:
            failed.append(token)
        print(f"{manga}: {i} / {number_chapters} completed", end = "\r")

    print()
    if failed:
        print("The following chapters have failed")
        for chapter in failed:
            print(chapter)
    else:
        print("No chapter has failed")


def download_and_zip(manga_title: str, chapter_number: int, chapter_path: str, printing_queue) -> bool:
    """ given path and chapter_path, create the zip file
    add a token to the queue when the process is done """

    page_number = 1
    url_chapter = f"https://official.lowee.us/manga/{manga_title}/{chapter_number:04d}-{page_number:03d}.png"
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
        url_chapter = f"https://official.lowee.us/manga/{manga_title}/{chapter_number:04d}-{page_number:03d}.png"

    zip_path = os.join(os.path.dirname(chapter_path), chapter_number)
    with ZipFile(zip_path, "a") as zip_file:
        pages = os.listdir(chapter_path)
        for page in pages:
            page_path = os.path.join(chapter_path, page)
            zip_file.write(page_path)

    file_name = None
    if not os.path.exists(zip_path):
        file_name = os.path.basename(zip_path)
    printing_queue.put(file_name)


def main() -> None:
    """ main function """
    
    # fetch html file
    manga_name = ARGS.name

    manga_folder = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), "MANGAS", manga_name)

    if os.path.exists(manga_folder):
        print("Folder already exists, adding new chapters")
    else:
        os.mkdir(manga_folder)

    number_chapters = 
    return

    # printing queue for communicating between the printer function and the pool
    printing_queue = multiprocessing.Manager().Queue()
    pool = multiprocessing.Pool()

    # set up the printing function
    pool.apply_async(printer, (manga_name, printing_queue, number_chapters))

    # set up the downloading and zipping process
    list_chapters = list(range(1, number_chapters+1))
    pool.starmap(download_and_zip, list_chapters)

    pool.close()
    pool.join()

if __name__ == "__main__":
    main()
