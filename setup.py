#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
import re

NAME='pyhecate'

readme_file = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'README.md')
with open(readme_file) as f:
    readme = f.read()

def get_version(*args):
    verstrline = open(os.path.join(NAME,"__init__.py"), "rt").read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    else:
        return "undefined"


def get_requirements(*args):
    """Get requirements from pip requirement files."""
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r'^#.*|\s#.*', '', line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r'\s+', '', line))
    return sorted(requirements)


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, *args)


setup(
    name=NAME,
    author='Adam Twardoch',
    author_email='adam+github@twardoch.com',
    url='https://twardoch.github.io/%s/' % (NAME),
    project_urls={
        'Source': "https://github.com/twardoch/%s/" % (NAME)
    },
    version=get_version(),
    license="MIT",
    description="Automagically generate thumbnails, animated GIFs, and summaries from videos (on macOS)",
    long_description=readme,
    long_description_content_type='text/markdown',
    python_requires='>=3.7',
    install_requires=get_requirements('requirements.txt'),
    extras_require={
        'dev': [
            'twine>=3.2.0'
        ]
    },
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='macos screenshot video computer-vision thumbnails frames video-summarization animated-gifs macosx video-thumbnail gif-maker generating-thumbnails thumbnail-images macos-app video-thumbnail-generator gif-thumbnail shot-boundary-detection video-summaries hecate extracting-key-frames gui',
    entry_points = '''
        [console_scripts]
        pyhecate=pyhecate.__main__:main
        '''
)
