import os
import setuptools
from distutils.core import setup, Extension

ENABLE_DEBUG = 'SAMPLE_DEBUG' in os.environ
if not ENABLE_DEBUG:
    from Cython.Build import cythonize
else:
    print("debug mode...")

PACKAGE_PATH = "pysample"

PACKAGES = setuptools.find_packages(PACKAGE_PATH)

EXTENSION_INCLUDE_DIRECTORIES = [
    "pysample/_c/",
]

CUR_SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))



CORE_SOURCES = [
    "pysample/_c/hash_map.c",
    "pysample/_c/sample_counter.c",
    "pysample/_c/sample_traceback.c",
]

CYTHON_EXTENSION_SOURCES = []
if not ENABLE_DEBUG:
    CYTHON_EXTENSION_SOURCES.append("pysample/_cython/sample.pyx")
else:
    CYTHON_EXTENSION_SOURCES.append("pysample/_cython/sample.c")


ext = [
    Extension(
        "pysample._cython.sample",
        sources=CYTHON_EXTENSION_SOURCES + CORE_SOURCES,
        include_dirs=EXTENSION_INCLUDE_DIRECTORIES,
        extra_compile_args=['-O0', '-g'],
        extra_link_args=[],
    ),
]


if not ENABLE_DEBUG:
    CYTHON_EXTENSION_MODULES = cythonize(ext)
else:
    CYTHON_EXTENSION_MODULES = ext

setup(
    name="pysample",
    packages=list(PACKAGES),
    ext_modules=CYTHON_EXTENSION_MODULES,
)
