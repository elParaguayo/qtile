from setuptools import build_meta as _orig
from setuptools.build_meta import *


def get_requires_for_build_wheel(config_settings=None):
    print("ADDING WLROOTS TP WHEEL REQUIREMENTS")
    return _orig.get_requires_for_build_wheel(config_settings) + ["pywlroots"]
