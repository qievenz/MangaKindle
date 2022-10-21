import requests
from typing import Dict, List
from bs4 import BeautifulSoup
from lib.Common import chapter_directory, exit_if_fails, load_json, network_error, not_found, success
from lib.results.manga_class import Chapter, Manga
from lib.MangaTemplate import MangaTemplate

PROVIDER_WEBSITE = "https://inmanga.com"
IMAGE_WEBSITE = f"{PROVIDER_WEBSITE}/page/getPageImage/?identification="
CHAPTERS_WEBSITE = f"{PROVIDER_WEBSITE}/chapter/getall?mangaIdentification="
SEARCH_URL = "https://inmanga.com/manga/getMangasConsultResult"
CHAPTER_PAGES_WEBSITE = f"{PROVIDER_WEBSITE}/chapter/chapterIndexControls?identification="

class InManga(MangaTemplate):
    def online_search(self, manga_name) -> List[Manga]:
        if self.search_results:
            return self.search_results
        
        data = {
            'hfilter[generes][]': '-1',
            'filter[queryString]': manga_name,
            'filter[skip]': '0',
            'filter[take]': '10',
            'filter[sortby]': '1',
            'filter[broadcastStatus]': '0',
            'filter[onlyFavorites]': 'false'
        }

        headers = {
            'Origin': 'https://inmanga.com',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Referer': 'https://inmanga.com/manga/consult?suggestion=' + manga_name,
            'X-Requested-With': 'XMLHttpRequest'
        }

        try:
            # Alternative Search: https://inmanga.com/OnMangaQuickSearch/Source/QSMangaList.json
            search = self.SCRAPER.post(SEARCH_URL, data=data, headers=headers)
            exit_if_fails(search)
        except requests.exceptions.ConnectionError:
            network_error()

        results_bea = BeautifulSoup(search.content, 'html.parser').find_all("a", href=True, recursive=False)

        for result_bea in results_bea:
            result = Manga()
            result.url = result_bea.get('href')
            if result.url is None:
                not_found()
            result.encoded_title = result.url.split('/')[-2] # encoded title
            result.uuid = result.url.split('/')[-1]
            result.title = result_bea.find('h4').get_text().strip() # may contain special characters
            
            self.search_results.append(result)
            
        return self.search_results
    
    def get_chapters(self) -> Dict[float, Chapter]:
        if self.current_manga.chapters:
            return self.current_manga.chapters
        
        chapters_json = self.scraper_get(CHAPTERS_WEBSITE + self.current_manga.uuid)
        chapters_full = load_json(chapters_json.content, 'data', 'result')
        #CHAPTERS_IDS = { float(chapter['Number']): chapter['Identification'] for chapter in chapters_full }
        for chapter in chapters_full:
            manga_chapter = Chapter()
            #manga_chapter.number = float(chapter['Number'])
            manga_chapter.uuid = chapter['Identification']
            manga_chapter.url = CHAPTER_PAGES_WEBSITE + manga_chapter.uuid
            
            self.current_manga.chapters[float(chapter['Number'])] = manga_chapter
        return self.current_manga.chapters
    
    def download_pages(self, chapter_num) -> None:
        manga_chapter = self.current_manga.chapters[chapter_num]
        try:
            chapter_page = self.scraper_get(manga_chapter.url)

            if success(chapter_page, print_ok=False):
                html = BeautifulSoup(chapter_page.content, 'html.parser')
                pages = html.find(id='PageList').find_all(True, recursive=False)
                for page in pages:
                    page_id = page.get('value')
                    page_number = int(page.get_text())
                    url = IMAGE_WEBSITE + page_id
                    chapter_dir = chapter_directory(self.current_manga.title, chapter_num)
                    self.download(page_number, url, chapter_dir, text=f'Page {page_number}/{len(pages)} ({100*page_number//len(pages)}%)')
        except requests.exceptions.ConnectionError:
            network_error()
