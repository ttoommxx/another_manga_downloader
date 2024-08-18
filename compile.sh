#!/bin/bash

if ! command -v pip &> /dev/null; then
    echo "Error: pip not installed."
    exit 1
fi

installed_packages=$(pip list)

if echo "$installed_packages" | grep "Nuitka"; then
	nuitka another_manga_downloader.py
elif echo "$installed_packages" | grep "pyinstaller"; then
	pyinstaller --onefile another_manga_downloader.py
else
	echo "Error: neither nuitka nor pyinstaller are installed via pip"
fi
