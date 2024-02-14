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
parser.add_argument("url")
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


def download_and_zip(zip_path: str, chapter_path: str, printing_queue: multiprocessing.Manager().Queue) -> bool:
    """ given path and chapter_path, create the zip file
    add a token to the queue when the process is done """
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
    
    url = ARGS.url
    manga_name = url.split("/")[-1]
    html_string = requests.get(url, timeout=30).text
    chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace("null", "None")
    list_chapters = ast.literal_eval(chapters_string)


    folder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MANGAS", manga_name)
    os.makedirs(folder_path, exist_ok=True)

    for chapter in list_chapters:
        chapter_number = f"{int(chapter["Chapter"][1:-1]):04d}"
        if chapter["Chapter"][-1] != "0":
            chapter_number += "." + str(chapter["Chapter"][-1])

        chapter_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MANGAS", manga_name, chapter_number)
        if os.path.exists(f"{chapter_path}.cbz"):
            continue
        os.makedirs(chapter_path, exist_ok=True)

        page_number = 0
        while True:
            page_number += 1

            url_chapter = f"https://official.lowee.us/manga/{manga_name}/{chapter_number}-{page_number:03d}.png"
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

    return


    # essential variables
    manga = os.path.basename(folder_path)
    cbz_folder_path = f"{folder_path}_CBZ"

    if os.path.exists(cbz_folder_path):
        if not os.path.isdir(cbz_folder_path):
            sys.exit(f"File with the name {manga}_CBZ already exists, rename and rerun the program")
        print("The folder alredy exists, adding missing files")
    else:
        os.mkdir(cbz_folder_path)

    # printing queue for communicating between the printer function and the pool
    printing_queue = multiprocessing.Manager().Queue()

    # create a list of chapters
    list_chapters = []
    for chapter in os.listdir(folder_path):
        chapter_path = os.path.join(folder_path, chapter)
        if not os.path.isdir( chapter_path ):
            continue # nothing to do

        zip_path = os.path.join(cbz_folder_path, f"{chapter}.cbz")
        if os.path.exists(zip_path):
            continue # skip if the file already exits

        list_chapters.append((zip_path, chapter_path, printing_queue))

    pool = multiprocessing.Pool()

    # set up the printing function
    number_chapters = len(list_chapters)
    pool.apply_async(printer, (manga, printing_queue, number_chapters))

    # set up the zipper processing of the chapters
    pool.starmap(zipper, list_chapters)

    pool.close()
    pool.join()

if __name__ == "__main__":
    main()
