#! /usr/bin/env python3
import os


# Get all files in a folder, recurivesly looking through all subfolders
def get_all_files(folder_path):
    """Get all files in a folder, recurivesly looking through all subfolders"""
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files






