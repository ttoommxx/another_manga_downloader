""" necessary modules """
import os
import argparse
import multiprocessing
import threading
import re
import ast
from zipfile import ZipFile
import requests

MAX_PROCESSES = min(os.cpu_count(), 4)

parser = argparse.ArgumentParser(prog="mangalife_downloader", description="download manga from mangalife")
parser.add_argument("urls", nargs="+")
ARGS = parser.parse_args() # args.picker contains the modality


def printer(manga_name: str, printing_queue: multiprocessing.Manager().Queue, number_chapters: int) -> None:
    """ function that updates the count of the executed chapters """
    print(f"- {manga_name}: 0 / {number_chapters} completed", end="\r")
    failed = []
    for i in range(1, number_chapters+1):
        token = printing_queue.get()
        if token == "quit":
            return
        if token:
            failed.append(token)
        print(f"- {manga_name}: {i} / {number_chapters} completed", end="\r")

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

    chapter_name_number = chapter["Chapter"]
    chapter_number = str(int(chapter_name_number[1:-1]))
    if chapter_name_number[-1] != "0":
        chapter_number += "." + str(chapter_name_number[-1])
    index = "-index-"+chapter_name_number[0] if chapter_name_number[0] != "1" else ""

    chapter_path = os.path.join(folder_path, chapter_name_number)
    
    failed_number = None
    if not os.path.exists(chapter_path + ".cbz"):
        os.makedirs(chapter_path, exist_ok=True)

        # DOWNLOAD
        pages = []
        page_number = 0
        while True:
            page_number += 1
            url_page = f"https://www.manga4life.com/read-online/{manga_name}-chapter-{chapter_number}{index}-page-{page_number}.html"
            response = requests.get(url_page, timeout=10)
            if response.status_code != 200 or "<title>404 Page Not Found</title>" in response.text:
                break
            
            # web scaping
            page_text = response.text
            server_name = re.findall(r"vm.CurPathName = \"(.*)\";", page_text)[0]
            server_directory = re.findall(r'vm.CurChapter = (.*);', page_text)[0].replace("null","None")
            server_directory = ast.literal_eval(server_directory)
            chap_num = server_directory["Chapter"]
            chap_num = chap_num[1:-1] if chap_num[-1] == "0" else chap_num[1:-1]+"."+chap_num[-1]
            chap_dir = server_directory["Directory"]
            chap_dir = chap_dir+"/" if chap_dir else chap_dir
            image_link = f"https://{server_name}/manga/{manga_name}/{chap_dir}{chap_num}-{page_number:03d}.png"
            response = requests.get(image_link, stream=True, timeout=10)
            if response.status_code != 200:
                break

            file_path = os.path.join(chapter_path, f"{page_number:03d}.png")
            if not os.path.exists(file_path):
                # open the file in binary write mode
                try:
                    with open(file_path, "wb") as page:
                        for chunk in response.iter_content(1024):
                            page.write(chunk)
                except KeyboardInterrupt:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return
            pages.append(file_path) 

        # ZIP
        zip_path = os.path.join(folder_path, chapter_name_number + ".cbz")
        try:
            with ZipFile(zip_path, "a") as zip_file:
                for page in pages:
                    page_path = os.path.join(chapter_path, page)
                    zip_file.write(page_path, page)
        except KeyboardInterrupt:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return

        # remove folder
        for page in pages:
            os.remove(page)
        if not os.listdir(chapter_path):
            os.rmdir(chapter_path)
        
        # save chapter name is fail
        if not os.path.exists(zip_path):
            failed_number = chapter_name_number

    printing_queue.put(failed_number)


def main() -> None:
    """ main function """
    
    print("Press CTRL+C to quit.")
    # fetch url and chapters data
    for url in ARGS.urls:
        manga_name = url.split("/")[-1]
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print("cannot request the mange, existing the program")
            return
        html_string = response.text
        chapters_string = re.findall(r"vm.Chapters = (.*);", html_string)[0].replace("null", "None")
        list_chapters = ast.literal_eval(chapters_string)

        # create folder if does not exists
        mangas_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Mangas")
        os.makedirs(mangas_path, exist_ok=True)
        folder_path = os.path.join(mangas_path, manga_name)
        os.makedirs(folder_path, exist_ok=True)

        # printing queue for communicating between the printer function and the pool
        manager = multiprocessing.Manager()
        printing_queue = manager.Queue()

        # add more to the list of chapters
        list_chapters = [[chapter, folder_path, printing_queue, manga_name] for chapter in list_chapters]
        number_chapters = len(list_chapters)

        # start processing pool
        pool = multiprocessing.Pool(processes=MAX_PROCESSES)

        # send all the processes to a pool
        printer_thread = threading.Thread(target=printer, daemon=True, args=(manga_name, printing_queue, number_chapters))
        printer_thread.start()
        try: # if CTRL+C stop execution
            pool.starmap(download_and_zip, list_chapters)
        except KeyboardInterrupt:
            print("\nProgram terminated")
            pool.terminate()
            
        pool.close()
        pool.join()
        printing_queue.put("quit")
        printer_thread.join()

        manager.shutdown()


if __name__ == "__main__":
    main()
