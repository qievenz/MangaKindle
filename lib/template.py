
import json
from abc import ABC, abstractmethod
import os
from typing import List, Tuple
from colorama import Fore, Style, init as init_console_colors

from lib.results.manga_class import Chapter, Manga

import cloudscraper
import bisect
import math

MANGA_DIR = './manga'
FILENAME_KEEP = set(['_', '-', ' ', '.'])
DIRECTORY_KEEP = FILENAME_KEEP | set(['/'])
EXTENSION_KEEP = set('.')
CHAPTERS_FORMAT = 'Format: start..end or chapters with commas. Example: --chapter 3 will download chapter 3, --chapter last will download the last chapter available, --chapters 3..last will download chapters from 3 to the last chapter, --chapter 3 will download only chapter 3, --chapters "3, 12" will download chapters 3 and 12, --chapters "3..12, 15" will download chapters from 3 to 12 and also chapter 15.'

class MangaTemplate(ABC):
    search_results: List[Manga]
    current_manga: Manga
    
    def __init__(self):
        self.search_results = []
        self.current_manga = Manga()
        self.SCRAPER = cloudscraper.create_scraper(browser = 'chrome', allow_brotli = False, debug = True)
        
    """
    The Abstract Class defines a template method that contains a skeleton of
    some algorithm, composed of calls to (usually) abstract primitive
    operations.

    Concrete subclasses should implement these operations, but leave the
    template method itself intact.
    """

    # These operations already have implementations.
    def get_scrapper(self, renew=False):
        if renew:
            self.SCRAPER = cloudscraper.create_scraper(delay=10,
                                        browser={
                                                'browser': 'chrome',
                                                'platform': 'android',
                                                'desktop': False
                                                },
                                        captcha={'provider': '2captcha'})
        return self.SCRAPER        
    
    def load_json(self, data, *keys):
        data = json.loads(data)
        for key in keys[:-1]:
            data = json.loads(data.get(key))
        return data.get(keys[-1])
    
    def print_colored(self, message, *colors, end='\n'):
        def printnoln(s):
            print(s, end='', flush=True)
        for color in colors:
            printnoln(color)
        print(message, end=end)
        printnoln(Style.RESET_ALL)
  
    def success(self, request, text='', ok=200, print_ok=True):
        if request.status_code == ok:
            if print_ok:
                self.print_colored(text if text else request.url, Fore.GREEN)
            return True
        else:
            text = f'{text}\n' if text else ''
            self.print_colored(f'{text}[{request.status_code}] {request.url}', Fore.RED)
            return False

    def exit_if_fails(self, request):
        if not self.success(request, print_ok=False):
            exit(1)
    
    def write_file(self, path, data):
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(path, 'wb') as handler:
            handler.write(data)
    
    def download(self, filename, url, directory='.', extension='png', text='', ok=200, headers=None):
        path = self.encode_path(filename, extension, directory)
        if os.path.isfile(path):
            text = text if text else path
            separation = ' ' * (20 - len(text))
            self.print_colored(f'{text}{separation}- Already exists', Fore.YELLOW)
            return False
        req = self.SCRAPER.get(url, headers=headers)
        if self.success(req, text, ok, print_ok=bool(text)):
            data = req.content
            self.write_file(path, data)
            return True
        return False
    
    def merge_intervals(self, chapter_intervals):
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

    def parse_chapter_intervals(self, chapter_intervals_str, last, start_end_sep='..', interval_sep=','):
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
            return self.merge_intervals(map(parse_chapter_interval, chapter_intervals_str.split(interval_sep)))
        except ValueError:
            self.error(f'Invalid chapters format', CHAPTERS_FORMAT)
    
    def error(self, message, tip=''):
        self.print_colored(message, Fore.RED, Style.BRIGHT)
        if tip:
            self.print_dim(tip)
        exit()
    
    def print_dim(self, s, *colors):
        self.print_colored(s, Style.DIM, *colors)
  
    def get_chapter_intervals(self, sorted_chapters:List[Chapter]) -> List[Tuple[float, float]]:
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

    def chapters_in_intervals(self, sorted_all_chapters, chapter_intervals):
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
            not_found_chapter_intervals = self.merge_intervals(not_found_chapter_intervals)

        return found_chapters, not_found_chapter_intervals

    def manga_directory(self, manga):
        return self.strip_path(f'{MANGA_DIR}/{manga}', DIRECTORY_KEEP)

    def chapter_directory(self, manga, chapter):
        return self.strip_path(f'{self.manga_directory(manga)}/{chapter:g}', DIRECTORY_KEEP)
    
    def strip_path(self, path, keep):
        return ''.join(c for c in path if c.isalnum() or c in keep).strip()

    def encode_path(self, filename, extension, directory='.'):
        return self.strip_path(f'{directory}/{filename}', DIRECTORY_KEEP) + '.' + self.strip_path(extension, EXTENSION_KEEP)

    def network_error(self):
        tip = 'Are you connected to Internet?'
        if True:#not args.cache:
            tip += '\nYou can use offline mode (using your already downloaded chapters) with --cache'
        self.error('Network error', tip)
  
    @abstractmethod
    def online_search(self, manga_name) -> List[Manga]:
        pass
    
    @abstractmethod
    def get_chapters(self) -> List[Chapter]:
        pass

    # @abstractmethod
    # def required_operations2(self) -> None:
    #     pass

    # These are "hooks." Subclasses may override them, but it's not mandatory
    # since the hooks already have default (but empty) implementation. Hooks
    # provide additional extension points in some crucial places of the
    # algorithm.

    def hook1(self) -> None:
        pass

    def hook2(self) -> None:
        pass
