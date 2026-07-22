import os, sys

_dll_dir = sys._MEIPASS if getattr(sys, "frozen", False) \
           else os.path.dirname(os.path.abspath(__file__))
os.add_dll_directory(_dll_dir)