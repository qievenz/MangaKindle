import argparse

from lib.Common import NAME, VERSION, check_version, is_python_version_supported, python_not_supported, print_colored
from colorama import Fore, Style

class CheckVersion(argparse.Action):
    def __init__(self, option_strings, version=VERSION, **kwargs):
        super(CheckVersion, self).__init__(option_strings, nargs=0, **kwargs)
        self.version = version
    
    def __call__(self, parser, namespace, values, option_string=None):
        if not is_python_version_supported():
            print_colored(python_not_supported(), Fore.RED)
        print_colored(NAME, Style.BRIGHT, end=' ')
        print_colored(self.version, Style.BRIGHT, Fore.CYAN)
        if check_version():
            print_colored('✅ Up to date', Fore.GREEN)
        exit()
        
