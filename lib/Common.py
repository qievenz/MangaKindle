
import urllib.parse
import bisect
import math
import re
import signal
import json
import sys
from typing import List, Tuple
from urllib import request
from colorama import Fore, Style, init as init_console_colors
import os
import subprocess
import platform
from lib.ArgsSingleService import ArgsSingleService
from lib.Constants import *
from lib.results.manga_class import Chapter

def load_json(data, *keys):
    data = json.loads(data)
    for key in keys[:-1]:
        data = json.loads(data.get(key))
    return data.get(keys[-1])

def print_colored(message, *colors, end='\n'):
    def printnoln(s):
        print(s, end='', flush=True)
    for color in colors:
        printnoln(color)
    print(message, end=end)
    printnoln(Style.RESET_ALL)

def success(request, text='', ok=200, print_ok=True):
    if request.status_code == ok:
        if print_ok:
            print_colored(text if text else request.url, Fore.GREEN)
        return True
    else:
        text = f'{text}\n' if text else ''
        print_colored(f'{text}[{request.status_code}] {request.url}', Fore.RED)
        return False

def exit_if_fails(request):
    if not success(request, print_ok=False):
        exit(1)

def not_found(manga):
  error(f"Manga '{manga}' not found")
  
def print_source(html_soup):
  print_dim(html_soup.prettify())
  
def cancellable():
  def cancel(s, f):
    print_dim('\nCancelled')
    exit()
  try:
    signal.signal(signal.SIGINT, cancel)
  except:
    pass
  
def write_file(path, data):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(path, 'wb') as handler:
        handler.write(data)

def check_version():
  args = ArgsSingleService().args
  latest_version = None
  try:
    response = request.get(f'https://api.github.com/repos/Carleslc/{NAME}/releases/latest')
    html_url = load_json(response.content, 'html_url')
    latest_version = load_json(response.content, 'tag_name')
  except:
    if not args.cache:
      print_dim(f'Cannot check for updates. Version: {VERSION}', Fore.YELLOW)
  if latest_version is None:
    return False
  is_updated = latest_version == VERSION
  if not is_updated:
    print_colored(f'New version is available! {VERSION} -> {latest_version}', Style.BRIGHT, Fore.GREEN)
    print_colored(f'Upgrade to the latest version: {html_url}', Fore.GREEN)
    if os.path.isdir('.git'):
      print_colored('Git detected. Do you want to checkout the new version❓ [Y/n]', Fore.YELLOW, Style.BRIGHT, end=' ')
      try:
        answer = input()
        if not answer or answer.lower() == 'y':
          subprocess.check_call(['git', 'fetch', 'origin', 'master'])
          subprocess.check_call(['git', 'checkout', latest_version])
      except:
        print('If you want to update later manually use ', end='')
        print_colored(f'git fetch && git checkout {latest_version}', Fore.YELLOW)
  return is_updated

def print_dim(s, *colors):
  print_colored(s, Style.DIM, *colors)
  
def is_python_version_supported():
  min_version, max_version = SUPPORT_PYTHON
  major, minor, _ = platform.python_version_tuple()
  major = int(major)
  minor = int(minor)
  return major >= min_version[0] and minor >= min_version[1] and major <= max_version[0] and minor <= max_version[1]

def python_not_supported():
  min_version, max_version = SUPPORT_PYTHON
  min_version = '.'.join(map(str, min_version))
  max_version = '.'.join(map(str, max_version))
  return f'Your Python version {platform.python_version()} is not fully supported ({sys.executable} --version). Please, use a Python version between {min_version} and {max_version}\n{RECOMMENDED_PYTHON}'

def network_error():
  args = ArgsSingleService().args
  tip = 'Are you connected to Internet?'
  if not args.cache:
    tip += '\nYou can use offline mode (using your already downloaded chapters) with --cache'
  error('Network error', tip)
  
def error(message, tip=''):
  print_colored(message, Fore.RED, Style.BRIGHT)
  if tip:
    print_dim(tip)
  exit()

def strip_path(path, keep):
  return ''.join(c for c in path if c.isalnum() or c in keep).strip()


def merge_intervals(chapter_intervals):
    # convert to list and sort intervals by start so overlapping intervals are next to each other
    overlapping_intervals = sorted(chapter_intervals, key=lambda chapter_interval: chapter_interval[0])

    # merge overlapping intervals to remove redundancy

    if len(overlapping_intervals) <= 1:
        return overlapping_intervals

    chapter_intervals = []
    current_start, current_end = overlapping_intervals[0]

    for other_start, other_end in overlapping_intervals[1:]:
        if other_start <= current_end and other_end >= current_start: # overlaps
            current_start = min(current_start, other_start)
            current_end = max(current_end, other_end)
        else:
            chapter_intervals.append((current_start, current_end))
            current_start = other_start
            current_end = other_end
    
    if not chapter_intervals or chapter_intervals[-1][1] != current_end: # last
        chapter_intervals.append((current_start, current_end))
    
    return chapter_intervals

def parse_chapter_intervals(chapter_intervals_str, last, start_end_sep='..', interval_sep=','):
    def parse_chapter(chapter):
        return last if chapter == 'last' else float(chapter)
    
    def parse_chapter_interval(chapter_interval_str):
        boundaries = chapter_interval_str.strip().split(start_end_sep)

        start_chapter = parse_chapter(boundaries[0])
        end_chapter = start_chapter
        
        for chapter in boundaries[1:]:
            chapter = parse_chapter(chapter)
            if chapter < start_chapter:
                start_chapter = chapter
            elif chapter > end_chapter:
                end_chapter = chapter
        
        return start_chapter, end_chapter

    try:
        return merge_intervals(map(parse_chapter_interval, chapter_intervals_str.split(interval_sep)))
    except ValueError:
        error(f'Invalid chapters format', CHAPTERS_FORMAT)

def get_chapter_intervals(sorted_chapters:List[Chapter]) -> List[Tuple[float, float]]:
    chapter_intervals = [] # list[(start, end)]

    if len(sorted_chapters) > 0:
        start_chapter = sorted_chapters[0]
        end_chapter = start_chapter

        for chapter in sorted_chapters:
            if chapter > end_chapter + 1:
                chapter_intervals.append((start_chapter, end_chapter))
                start_chapter = chapter
            end_chapter = chapter
        
        chapter_intervals.append((start_chapter, end_chapter))
    
    return chapter_intervals

def chapters_in_intervals(sorted_all_chapters, chapter_intervals):
    found_chapters = []
    not_found_chapter_intervals = []

    for start_chapter, end_chapter in chapter_intervals:
        # find index of first chapter available greater or equal than start_chapter
        i = bisect.bisect_left(sorted_all_chapters, start_chapter)
        
        if i < len(sorted_all_chapters):
            chapter = sorted_all_chapters[i]
            in_interval = chapter <= end_chapter
            
            if chapter > start_chapter and in_interval:
                not_found_end_chapter = math.ceil(chapter - 1)
                if not_found_end_chapter < start_chapter:
                    not_found_end_chapter = start_chapter
                not_found_chapter_intervals.append((start_chapter, not_found_end_chapter))

            next_int_chapter = None

            # add chapters while they are included in the interval
            while in_interval:
                found_chapters.append(chapter)

                # add chapters in between as not found
                if next_int_chapter is not None and next_int_chapter < chapter:
                    not_found_chapter_intervals.append((next_int_chapter, math.ceil(chapter - 1)))
                
                # next chapter
                i += 1
                if i < len(sorted_all_chapters):
                    next_int_chapter = math.floor(chapter + 1)
                    chapter = sorted_all_chapters[i]
                    in_interval = chapter <= end_chapter
                else:
                    in_interval = False
            
            # add the interval chapters that cannot be found
            last_chapter_found = found_chapters[-1] if found_chapters else None
            if not found_chapters or last_chapter_found < start_chapter:
                not_found_chapter_intervals.append((start_chapter, end_chapter))
            elif last_chapter_found < end_chapter:
                not_found_start_chapter = math.floor(last_chapter_found + 1)
                if not_found_start_chapter > end_chapter:
                    not_found_start_chapter = end_chapter
                not_found_chapter_intervals.append((not_found_start_chapter, end_chapter))
            else:
                not_found_chapter_intervals.append((start_chapter, end_chapter))
        
    if not_found_chapter_intervals:
        not_found_chapter_intervals = merge_intervals(not_found_chapter_intervals)

    return found_chapters, not_found_chapter_intervals

def manga_directory(manga):
    return strip_path(f'{MANGA_DIR}/{manga}', DIRECTORY_KEEP)

def chapter_directory(manga, chapter):
    return strip_path(f'{manga_directory(manga)}/{chapter:g}', DIRECTORY_KEEP)

def encode(title):
  return re.sub(r'\W+', '-', title)

def encode_path(filename, extension, directory='.'):
    return strip_path(f'{directory}/{filename}', DIRECTORY_KEEP) + '.' + strip_path(extension, EXTENSION_KEEP)

def chapters_to_intervals_string(sorted_chapters, start_end_sep='-', interval_sep=','):
    chapter_intervals = get_chapter_intervals(sorted_chapters)
    return join_chapter_intervals(chapter_intervals, start_end_sep=start_end_sep, interval_sep=interval_sep)

def join_chapter_intervals(chapter_intervals, start_end_sep='..', interval_sep=','):
    def chapter_interval_str(chapter_interval):
        start, end = chapter_interval
        return f'{start:g}{start_end_sep}{end:g}' if start != end else f'{start:g}'
    return interval_sep.join(map(chapter_interval_str, chapter_intervals))
  

def decode(title):
  return title.replace('-', ' ')

def plural(size):
  return 's' if size != 1 else ''

def check_exists_file(path):
  if os.path.isfile(path):
    print_colored(f'{path} - Already exists', Fore.YELLOW)
    return True
  return False
def files(dir, extension=''):
  if not os.path.isdir(dir):
    error(f'{dir} does not exist!')
  def filename(file):
    return file.split('.')[-2]
  for file in os.listdir(dir):
    path = os.path.abspath(f'{dir}/{file}')
    if os.path.isfile(path) and file.endswith(extension):
      yield filename(file), path

def folders(dir):
  if not os.path.isdir(dir):
    error(f'{dir} does not exist');
  for subdir in os.listdir(dir):
    path = os.path.abspath(f'{dir}/{subdir}')
    if os.path.isdir(path):
      yield subdir, path

def copy_all(name_path_list, to_path):
  import errno, shutil
  def copy(src, dest):
    try:
      shutil.copytree(src, dest)
    except OSError as e:
      if e.errno == errno.ENOTDIR: # src is file
        shutil.copy(src, dest)
      else:
        error(e)
  for name, path in name_path_list:
    copy(path, f'{to_path}/{name}')


def split_rotate_2_pages(rotate):
  return str(1 if rotate else 0)

def single(single):
  return str(0 if single else 2)

def removeAlpha(image_path):
  import wand.image
  with wand.image.Image(filename=image_path) as img:
    if img.alpha_channel:
      img.alpha_channel = 'remove'
      img.background_color = wand.image.Color('white')    
      img.save(filename=image_path)

def convert_to_pdf(path, chapters_paths):
  args = ArgsSingleService().args
  if not check_exists_file(path):
    if args.remove_alpha:
      print_dim(f'Removing alpha channel from images for {path}')
      for img_path in chapters_paths:
        removeAlpha(img_path)
    with open(path, "wb") as f:
      import img2pdf
      f.write(img2pdf.convert(chapters_paths))
    print_colored(f'DONE: {os.path.abspath(path)}', Fore.GREEN, Style.BRIGHT)

def fix_corrupted_file(corrupted_file, corrupted_file_path, argv):
  print_colored(f'{corrupted_file} is corrupted, removing and trying again... (Cancel with Ctrl+C)', Fore.RED)
  local_corrupted_file_path = os.path.abspath(f'{corrupted_file_path}/{corrupted_file}')
  print_dim(local_corrupted_file_path)
  os.remove(local_corrupted_file_path)
  if corrupted_file_path != local_corrupted_file_path:
    os.remove(corrupted_file_path)
  cache_convert(argv)

def convert_except(e, argv):
  message = str(e)
  corrupted_file_path = re.findall(r'Image file (.*?) is corrupted', message)
  if len(corrupted_file_path) > 0:
    parts = corrupted_file_path[0].split('/')
    corrupted_file = f'{parts[-2]}/{parts[-1]}'
    fix_corrupted_file(corrupted_file, os.path.abspath(corrupted_file_path[0]), argv)
  elif message.startswith('("One of workers crashed. Cause: \'float\' object cannot be interpreted as an integer"'):
    tip = 'https://github.com/Carleslc/InMangaKindle/issues/13'
    python_supported = is_python_version_supported()
    if not python_supported:
      tip = python_not_supported() + '\n' + tip
    error(tip, message)
  else:
    import traceback
    traceback.print_tb(e.__traceback__)
    error(e)

def cache_convert(argv):
  from kindlecomicconverter.comic2ebook import main as manga2ebook
  try:
    manga2ebook(argv)
  except Exception as e:
    convert_except(e, argv)
    
def encode_url_format(name):
  return urllib.parse.quote(name)