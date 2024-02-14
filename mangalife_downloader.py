""" necessary modules """
import os
import argparse
import multiprocessing
import re
import ast
import shutil
from zipfile import ZipFile
import requests

MAX_PROCESSES = os.cpu_count()

parser = argparse.ArgumentParser(prog="mangalife_downloader", description="download manga from mangalife")
parser.add_argument("url")
ARGS = parser.parse_args() # args.picker contains the modality


def printer(manga_name: str, printing_queue: multiprocessing.Manager().Queue, number_chapters: int) -> None:
    """ function that updates the count of the executed chapters """
    print(f" {manga_name}: 0 / {number_chapters} completed", end="\r")
    failed = []
    for i in range(1, number_chapters+1):
        token = printing_queue.get()
        if token:
            failed.append(token)
        print(f" {manga_name}: {i} / {number_chapters} completed", end="\r")

    print()
    if failed:
        print("The following chapters have failed")
        for chapter in failed:
            print(chapter)
    else:
        print("No chapter has failed")


def download_and_zip(chapter: dict, folder_path: str, printing_queue: multiprocessing.Manager().Queue, manga_name: str) -> bool:
    """ given path and chapter_path, create the zip file
    add a token to the queue when the process is done """

    chapter_number = chapter["Chapter"]
    chapter_number_format = f"{int(chapter_number[1:-1]):04d}"
    if chapter_number[-1] != "0":
        chapter_number_format += "." + str(chapter_number[-1])

    chapter_path = os.path.join(folder_path, chapter_number)
    
    failed_number = None
    if not os.path.exists(chapter_path + ".cbz"):
        os.makedirs(chapter_path, exist_ok=True)

        # DOWNLOAD
        page_number = 0
        while True:
            page_number += 1
            url_chapter = f"https://official.lowee.us/manga/{
                manga_name}/{chapter_number_format}-{page_number:03d}.png"
            response = requests.get(url_chapter, stream=True, timeout=10)
            if response.status_code != 200:
                break

            file_path = os.path.join(chapter_path, f"{page_number:03d}.png")
            if not os.path.exists(file_path):
                # open the file in binary write mode
                with open(file_path, "wb") as page:
                    for chunk in response.iter_content(1024):
                        page.write(chunk)

        # ZIP
        zip_path = os.path.join(folder_path, chapter_number + ".cbz")
        with ZipFile(zip_path, "a") as zip_file:
            pages = os.listdir(chapter_path)
            for page in pages:
                page_path = os.path.join(chapter_path, page)
                zip_file.write(page_path, page)

        # remove folder
        shutil.rmtree(chapter_path)
        
        # save chapter name is fail
        if not os.path.exists(zip_path):
            failed_number = os.path.basename(zip_path)

    printing_queue.put(failed_number)


def main() -> None:
    """ main function """
    
    # fetch url and chapters data
    url = ARGS.url
    manga_name = url.split("/")[-1]
    html_string = requests.get(url, timeout=30).text
    chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace("null", "None")
    list_chapters = ast.literal_eval(chapters_string)

    # create folder if does not exists
    folder_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "MANGAS", manga_name)
    os.makedirs(folder_path, exist_ok=True)

    # printing queue for communicating between the printer function and the pool
    printing_queue = multiprocessing.Manager().Queue()

    # add more to the list of chapters
    list_chapters = [[chapter, folder_path, printing_queue, manga_name] for chapter in list_chapters]

    # start processing pool
    pool = multiprocessing.Pool(processes=MAX_PROCESSES+1)

    # set up the printing function
    number_chapters = len(list_chapters)
    pool.apply_async(printer, (manga_name, printing_queue, number_chapters))

    # set up the zipper processing of the chapters
    pool.starmap(download_and_zip, list_chapters)

    pool.close()
    pool.join()

if __name__ == "__main__":
    main()
