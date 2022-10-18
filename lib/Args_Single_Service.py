import argparse

from lib.Constants import CHAPTERS_FORMAT, MANGA_DIR, NAME, VERSION, WEBSITE

class Args_Single_Service(object):
  _shared_borg_state = {}
      
  def __new__(cls, *args, **kwargs):
    obj = super(Args_Single_Service, cls).__new__(cls, *args, **kwargs)
    obj.__dict__ = cls._shared_borg_state
    return obj

def set_args(checkversion):
  parser = argparse.ArgumentParser(prog=NAME, epilog=f'web: {WEBSITE}')
  parser.add_argument("manga", help="manga to download", nargs='+')
  parser.add_argument("--chapters", "--chapter", help=f'chapters to download. {CHAPTERS_FORMAT} If this argument is not provided all chapters will be downloaded.', nargs='+')
  parser.add_argument("--directory", help=f"directory to save downloads. Default: {MANGA_DIR}", default=MANGA_DIR)
  parser.add_argument("--single", action='store_true', help="merge all chapters in only one file. If this argument is not provided every chapter will be in a different file")
  parser.add_argument("--rotate", action='store_true', help="rotate double pages. If this argument is not provided double pages will be splitted in 2 different pages")
  parser.add_argument("--profile", help='Device profile (Available options: K1, K2, K34, K578, KDX, KPW, KV, KO, KoMT, KoG, KoGHD, KoA, KoAHD, KoAH2O, KoAO) [Default = KPW (Kindle Paperwhite)]', default='KPW')
  parser.add_argument("--format", help='Output format (Available options: PNG, PDF, MOBI, EPUB, CBZ) [Default = MOBI]. If PNG is selected then no conversion to e-reader file will be done', default='MOBI')
  parser.add_argument("--fullsize", action='store_true', help="Do not stretch images to the profile's device resolution")
  parser.add_argument("--cache", action='store_true', help="Avoid downloading chapters and use already downloaded chapters instead (offline)")
  parser.add_argument("--remove-alpha", action='store_true', help="When converting to PDF remove alpha channel on images using ImageMagick Wand")
  parser.add_argument("--version", "-v", action=checkversion, help="Display current InMangaKindle version", version=VERSION)
  return parser.parse_args()

