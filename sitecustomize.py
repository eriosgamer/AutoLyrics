import site
import sys
import os

venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv')
site_packages = os.path.join(venv, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
if os.path.isdir(site_packages):
    site.addsitedir(site_packages)
