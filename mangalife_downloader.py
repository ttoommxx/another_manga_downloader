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
    manga_title = url.split("/")[-1]
    html_string = requests.get(url).text
    chapters_string = re.findall(
        r"vm.Chapters = (.*);", html_string)[0].replace("null", "None")
    list_chapters = ast.literal_eval(chapters_string)


    # for chapter in list_chapters:
    #     chapter_number = int(chapter["Chapter"][1:-1])
    #     page_number = 1
    #     while True:
    #         url_chapter = f"https://www.manga4life.com/read-online/{
    #             MANGA}-chapter-{chapter_number}-page-{page_number}.html"
    #         page_string = requests.get(url_chapter).text
    #         if "404 Page Not Found" in page_string:
    #             break

    #         # here do stuff

    #         page_number += 1

    #     break



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
