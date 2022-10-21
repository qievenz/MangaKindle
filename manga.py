#!/usr/bin/python3
# -*- coding: utf-8 -*-

from lib.ArgsSingleService import ArgsSingleService, set_args
import os
import sys
import tempfile
import subprocess
from multiprocessing import freeze_support
from lib.CheckVersion import CheckVersion
from lib.Common import *
from lib.LocalManga import LocalManga
from lib.OnlineMangaTemplate import OnlineMangaTemplate
from lib.results.manga_class import Manga

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


from lib.MangaTemplate import MangaTemplate
from lib.InManga import InManga
from lib.LectorManga import LectorManga
from colorama import Fore, Style, init as init_console_colors


def create_manga_service_and_search_online(title) -> List[OnlineMangaTemplate]:
  results = []
  for subclass in OnlineMangaTemplate.__subclasses__():
    manga_class = subclass()
    manga_class.base_search(title)
    if manga_class.search_results: results.append(manga_class)
  if not results: not_found(title)
  return results

def title_selection(manga_services) -> MangaTemplate:
  option = 0
  for manga_service in manga_services:
    for title in manga_service.search_results:
      print(f"[{option}] {manga_service.name} - {title.title}")
      option += 1
  selection = int(input("Select title: "))
  for manga_service in manga_services:
    if selection > len(manga_service.search_results):
      selection -= len(manga_service.search_results)
      continue
    else:
      manga_service.current_manga = manga_service.search_results[selection]
      return manga_service

if __name__ == "__main__":
  cancellable()
  freeze_support()
  init_console_colors()
  
  # PARSE ARGS
  ass = ArgsSingleService()
  ass.args = set_args(CheckVersion)
  args = ass.args

  check_version()

  MANGA_DIR = strip_path(args.directory, DIRECTORY_KEEP)

  if not args.profile:
    args.profile = 'KPW'

  MANGA = ' '.join(args.manga)

  search_type = f'in {MANGA_DIR}' if args.cache else 'online'

  manga_service = None
  if args.cache: # offline search
    manga_service = LocalManga()
    manga_service.base_search(MANGA)
    manga_service = title_selection([manga_service])
  else: # online search
    manga_services = create_manga_service_and_search_online(MANGA)
    manga_service = title_selection(manga_services)

  print_colored(manga_service.current_manga.title, Fore.BLUE)

  # RETRIEVE CHAPTERS

  directory = os.path.abspath(manga_directory(manga_service.current_manga.title))

  ALL_CHAPTERS = manga_service.get_chapters()

  if not ALL_CHAPTERS:
    error(f"There are no chapters of '{manga_service.current_manga.title}' available {search_type}")
  
  ALL_CHAPTERS = sorted(ALL_CHAPTERS)

  last = ALL_CHAPTERS[-1]
  
  CHAPTER_INTERVALS = parse_chapter_intervals(' '.join(args.chapters), last.number) if args.chapters else get_chapter_intervals(ALL_CHAPTERS)

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
      print_colored(f'Downloading {manga_service.current_manga.title} {chapter:g}', Fore.YELLOW, Style.BRIGHT)

      manga_service.get_pages(chapter)

  extension = f'.{args.format.lower()}'
  args.format = args.format.upper()

  if args.format != 'PNG':
    print_colored(f'Converting to {args.format}...', Fore.BLUE, Style.BRIGHT)

    if args.format == 'PDF':
      chapters_paths = []
      for chapter in CHAPTERS:
        chapter_dir = chapter_directory(manga_service.current_manga.title, chapter)
        page_number_paths = sorted(list(files(chapter_dir, 'png')), key=lambda page_path: int(page_path[0]))
        page_paths = list(map(lambda page_path: page_path[1], page_number_paths))
        if args.single:
          chapters_paths.extend(page_paths)
        else:
          path = f'{MANGA_DIR}/{manga_service.current_manga.title} {chapter:g}{extension}'
          convert_to_pdf(path, page_paths)
      if args.single:
        chapter_interval = chapters_to_intervals_string(CHAPTERS)
        path = f'{MANGA_DIR}/{manga_service.current_manga.title} {chapter_interval}{extension}'
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
          copy_all([(chapter, chapter_directory(manga_service.current_manga.title, chapter)) for chapter in CHAPTERS], temp)
          title = f'{manga_service.current_manga.title} {chapter_interval}'
          print_colored(title, Fore.BLUE)
          argv = argv + ['--title', title, temp] # all chapters in manga directory are packed
          cache_convert(argv)
          path = f'{MANGA_DIR}/{manga_service.current_manga.title} {chapter_interval}{extension}'
          os.rename(f'{MANGA_DIR}/{os.path.basename(temp)}{extension}', path)
          print_colored(f'DONE: {os.path.abspath(path)}', Fore.GREEN, Style.BRIGHT)
      else:
        for chapter in CHAPTERS:
          title = f'{manga_service.current_manga.title} {chapter:g}'
          print_colored(title, Fore.BLUE)
          argv_chapter = argv + ['--title', title, chapter_directory(manga_service.current_manga.title, chapter)]
          cache_convert(argv_chapter)
          path = f'{MANGA_DIR}/{manga_service.current_manga.title} {chapter:g}{extension}'
          os.rename(f'{MANGA_DIR}/{chapter:g}{extension}', path)
          print_colored(f'DONE: {os.path.abspath(path)}', Fore.GREEN, Style.BRIGHT)
  else:
    if len(CHAPTERS) == 1:
      directory = os.path.abspath(chapter_directory(manga_service.current_manga.title, CHAPTERS[0]))
      chapter_intervals_info = ''
    else:
      chapter_intervals_info = f" ({chapters_to_intervals_string(CHAPTERS, interval_sep=', ')})"
    print_colored(f'DONE: {directory}{chapter_intervals_info}', Fore.GREEN, Style.BRIGHT)
