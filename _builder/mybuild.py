from setuptools import build_meta as _orig
from setuptools.build_meta import *
import sys


def get_requires_for_build_wheel(config_settings=None):
    print("ADDING WLROOTS TP WHEEL REQUIREMENTS")
    print(config_settings)
    print(_orig._BACKEND.__dict__)
    print(sys.argv)
    return _orig.get_requires_for_build_wheel(config_settings) + ["pywlroots"]
