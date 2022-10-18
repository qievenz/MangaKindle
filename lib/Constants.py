VERSION = '1.6'

NAME = 'InMangaKindle'
WEBSITE = 'https://carleslc.me/InMangaKindle/'
CHAPTERS_FORMAT = 'Format: start..end or chapters with commas. Example: --chapter 3 will download chapter 3, --chapter last will download the last chapter available, --chapters 3..last will download chapters from 3 to the last chapter, --chapter 3 will download only chapter 3, --chapters "3, 12" will download chapters 3 and 12, --chapters "3..12, 15" will download chapters from 3 to 12 and also chapter 15.'
SUPPORT_PYTHON = [(3,6,0), (3,9,9)]
RECOMMENDED_PYTHON = 'https://www.python.org/downloads/release/python-399/'
MANGA_DIR = './manga'
FILENAME_KEEP = set(['_', '-', ' ', '.'])
DIRECTORY_KEEP = FILENAME_KEEP | set(['/'])
EXTENSION_KEEP = set('.')