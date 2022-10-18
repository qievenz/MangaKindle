#!/usr/bin/python3
# -*- coding: utf-8 -*-

VERSION = '1.6'

NAME = 'InMangaKindle'
WEBSITE = 'https://carleslc.me/InMangaKindle/'

SUPPORT_PYTHON = [(3,6,0), (3,9,9)]
RECOMMENDED_PYTHON = 'https://www.python.org/downloads/release/python-399/'
from args_service import set_args, args
import os
import re
import sys
import math
import json
import signal
import argparse
import tempfile
import bisect
import platform
import subprocess
from multiprocessing import freeze_support
from typing import List, Tuple
from lib.CheckVersion import CheckVersion
from lib.Common import *
from lib.results.manga_class import Manga

from lib.template import MangaTemplate
from lib.inmanga import InManga
from lib.lectormanga import LectorManga

def install_dependencies(dependencies_file):
  # Check dependencies
  from pathlib import Path
  import pkg_resources
  dependencies_path = Path(__file__).with_name(dependencies_file)
  dependencies = pkg_resources.parse_requirements(dependencies_path.open())
  try:
    for dependency in dependencies:
      dependency = str(dependency)
      pkg_resources.require(dependency)
  except pkg_resources.DistributionNotFound as e:
    print("Some dependencies are missing, installing...")
    # Install missing dependencies
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", dependencies_file])

install_dependencies("dependencies.txt")

import requests
import cloudscraper
from bs4 import BeautifulSoup
from colorama import Fore, Style, init as init_console_colors

PROVIDER_WEBSITE = "https://inmanga.com"
IMAGE_WEBSITE = f"{PROVIDER_WEBSITE}/page/getPageImage/?identification="
CHAPTERS_WEBSITE = f"{PROVIDER_WEBSITE}/chapter/getall?mangaIdentification="
CHAPTER_PAGES_WEBSITE = f"{PROVIDER_WEBSITE}/chapter/chapterIndexControls?identification="
MANGA_WEBSITE = f"{PROVIDER_WEBSITE}/ver/manga"

SEARCH_URL = "https://inmanga.com/manga/getMangasConsultResult"

MANGA_DIR = './manga'

FILENAME_KEEP = set(['_', '-', ' ', '.'])
DIRECTORY_KEEP = FILENAME_KEEP | set(['/'])
EXTENSION_KEEP = set('.')

SCRAPER = cloudscraper.create_scraper()

CHAPTERS_FORMAT = 'Format: start..end or chapters with commas. Example: --chapter 3 will download chapter 3, --chapter last will download the last chapter available, --chapters 3..last will download chapters from 3 to the last chapter, --chapter 3 will download only chapter 3, --chapters "3, 12" will download chapters 3 and 12, --chapters "3..12, 15" will download chapters from 3 to 12 and also chapter 15.'




def create_manga_service_and_search_online(manga_name) -> MangaTemplate:
  for subclass in MangaTemplate.__subclasses__():
    manga_class = subclass()
    manga_class.online_search(manga_name)
    if manga_class.search_results: break
  if subclass is None:
      raise ValueError("No Manga implementation found " + repr(manga_name))
  return manga_class
    
if __name__ == "__main__":
  cancellable()
  freeze_support()
  init_console_colors()
  
  # PARSE ARGS
  set_args(CheckVersion)

  check_version()

  MANGA_DIR = strip_path(args.directory, DIRECTORY_KEEP)

  if not args.profile:
    args.profile = 'KPW'

  MANGA = ' '.join(args.manga)

  # SEARCH ANIME

  search_type = f'in {MANGA_DIR}' if args.cache else 'online'
  print_colored(f"Searching '{MANGA}' {search_type}...", Style.BRIGHT)

  results = []
  manga = Manga()
  match = False
  if args.cache: # offline search
    encoded_title = encode(MANGA).upper()
    for cached in folders(MANGA_DIR):
      manga = cached[0]
      encoded_cached = manga.upper()
      manga.title = decode(manga)
      if encoded_title == encoded_cached:
        match = True
        break
      elif encoded_cached in encoded_title or encoded_title in encoded_cached:
        results.append(manga.title)
        submatch_manga = manga
  else: # online search
    manga_service = create_manga_service_and_search_online(MANGA)
    manga_service.network_error()
    results = manga_service.search_results
    for result in results:
      if result.title.upper().strip() == MANGA.upper().strip():
        match = True
        manga_service.current_manga = result
        manga = manga_service.current_manga
        break

  if not match:
    if len(results) > 1:
      upper_titles = [title.title.upper() for title in results]
      error('There are several results, please select one of these:\n' + '\n'.join(upper_titles))
    elif len(results) == 1:
      manga = results[0]
      if args.cache:
        manga = submatch_manga
    else:
      not_found()

  print_colored(manga.title, Fore.BLUE)

  # RETRIEVE CHAPTERS

  directory = os.path.abspath(manga_service.manga_directory(manga.title))

  if args.cache:
    ALL_CHAPTERS = [float(chapter[0]) for chapter in folders(directory)]
  else:
    ALL_CHAPTERS = manga_service.get_chapters()
    #ALL_CHAPTERS = CHAPTERS_IDS.keys()

  if not ALL_CHAPTERS:
    error(f"There are no chapters of '{manga.title}' available {search_type}")
  
  ALL_CHAPTERS = sorted(ALL_CHAPTERS)

  last = ALL_CHAPTERS[-1]
  
  CHAPTER_INTERVALS = manga_service.parse_chapter_intervals(' '.join(args.chapters), last.number) if args.chapters else manga_service.get_chapter_intervals(ALL_CHAPTERS)

  CHAPTERS, chapters_not_found_intervals = chapters_in_intervals(ALL_CHAPTERS, CHAPTER_INTERVALS)

  if args.cache:
    print_colored(f'Last downloaded chapter: {last:g}', Fore.YELLOW, Style.BRIGHT)
  else:
    print_dim(f'{len(CHAPTERS)} chapter{plural(len(CHAPTERS))} will be downloaded - Cancel with Ctrl+C')

  if chapters_not_found_intervals:
    chapters_not_found_intervals = join_chapter_intervals(chapters_not_found_intervals, interval_sep=', ')
    not_found = 'are not downloaded' if args.cache else 'could not be found'
    print_colored(f'The following chapters {not_found}: {chapters_not_found_intervals}', Fore.RED, Style.BRIGHT)
    if args.cache:
      error(f'Please download those chapters first.', 'Try again this command without --cache')
    else:
      print_colored('🖐️  Press enter to continue without those chapters or Ctrl+C to abort...', Fore.MAGENTA, Style.BRIGHT, end=' ')
      input()
  
  if not CHAPTERS:
    error("No chapters found")

  if not args.cache:
    # DOWNLOAD CHAPTERS

    for chapter in CHAPTERS:
      print_colored(f'Downloading {manga.title} {chapter:g}', Fore.YELLOW, Style.BRIGHT)

      manga_service.download_pages(chapter)

  extension = f'.{args.format.lower()}'
  args.format = args.format.upper()

  if args.format != 'PNG':
    print_colored(f'Converting to {args.format}...', Fore.BLUE, Style.BRIGHT)

    if args.format == 'PDF':
      import img2pdf
      if args.remove_alpha:
        import wand.image
      chapters_paths = []
      for chapter in CHAPTERS:
        chapter_dir = manga_service.chapter_directory(manga.title, chapter)
        page_number_paths = sorted(list(files(chapter_dir, 'png')), key=lambda page_path: int(page_path[0]))
        page_paths = list(map(lambda page_path: page_path[1], page_number_paths))
        if args.single:
          chapters_paths.extend(page_paths)
        else:
          path = f'{MANGA_DIR}/{manga.title} {chapter:g}{extension}'
          convert_to_pdf(path, page_paths)
      if args.single:
        chapter_interval = chapters_to_intervals_string(CHAPTERS)
        path = f'{MANGA_DIR}/{manga.title} {chapter_interval}{extension}'
        convert_to_pdf(path, chapters_paths)
    else:
      # CONVERT TO E-READER FORMAT
      from kindlecomicconverter.comic2ebook import main as manga2ebook

      argv = ['--output', MANGA_DIR, '-p', args.profile, '--manga-style', '--hq', '-f', args.format, '--batchsplit', single(args.single), '-u', '-r', split_rotate_2_pages(args.rotate)]
      
      if not args.fullsize:
        argv.append('-s')

      if args.single:
        chapter_interval = chapters_to_intervals_string(CHAPTERS)
        with tempfile.TemporaryDirectory() as temp:
          copy_all([(chapter, manga_service.chapter_directory(manga.title, chapter)) for chapter in CHAPTERS], temp)
          title = f'{manga.title} {chapter_interval}'
          print_colored(title, Fore.BLUE)
          argv = argv + ['--title', title, temp] # all chapters in manga directory are packed
          cache_convert(argv)
          path = f'{MANGA_DIR}/{manga.title} {chapter_interval}{extension}'
          os.rename(f'{MANGA_DIR}/{os.path.basename(temp)}{extension}', path)
          print_colored(f'DONE: {os.path.abspath(path)}', Fore.GREEN, Style.BRIGHT)
      else:
        for chapter in CHAPTERS:
          title = f'{manga.title} {chapter:g}'
          print_colored(title, Fore.BLUE)
          argv_chapter = argv + ['--title', title, manga_service.chapter_directory(manga.title, chapter)]
          cache_convert(argv_chapter)
          path = f'{MANGA_DIR}/{manga.title} {chapter:g}{extension}'
          os.rename(f'{MANGA_DIR}/{chapter:g}{extension}', path)
          print_colored(f'DONE: {os.path.abspath(path)}', Fore.GREEN, Style.BRIGHT)
  else:
    if len(CHAPTERS) == 1:
      directory = os.path.abspath(manga_service.chapter_directory(manga.title, CHAPTERS[0]))
      chapter_intervals_info = ''
    else:
      chapter_intervals_info = f" ({chapters_to_intervals_string(CHAPTERS, interval_sep=', ')})"
    print_colored(f'DONE: {directory}{chapter_intervals_info}', Fore.GREEN, Style.BRIGHT)
