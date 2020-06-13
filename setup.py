import os
import sys
import setuptools
from distutils.core import setup, Extension

ENABLE_DEBUG = 'SAMPLE_DEBUG' in os.environ
if not ENABLE_DEBUG:
    from Cython.Build import cythonize
else:
    print("debug mode...")


PACKAGES = setuptools.find_packages()

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


version = sys.version_info[:2]
if version < (3, 7):
    print('pysample requires Python version 3.7 or later' +
          ' ({}.{} detected).'.format(*version))
    sys.exit(-1)


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

install_requires = []

VERSION = '1.0.0'

setup(
    name="pysample-profiler",
    version=VERSION,
    description="Sampling profiler for Python programs",
    author='James Xie',
    author_email='yanyin0703@163.com',
    url='https://github.com/James-xie/pysample',
    license='MIT',
    packages=list(PACKAGES),
    install_requires=install_requires,
    ext_modules=CYTHON_EXTENSION_MODULES,
    entry_points={
        'console_scripts': ['pysample=pysample.command_line:main'],
    }
)
