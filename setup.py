#!/usr/bin/env python3

import os
import re

from setuptools import find_packages, setup

NAME = "pyhecate"

readme_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
with open(readme_file, encoding="utf-8") as f:
    readme = f.read()


def get_version(*args):
    with open(os.path.join(NAME, "__init__.py"), encoding="utf-8") as f:
        verstrline = f.read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    return "undefined"


def get_requirements(*args):
    """Get requirements from pip requirement files."""
    requirements = set()
    with open(get_absolute_path(*args), encoding="utf-8") as handle:
        for line_content in handle:
            # Strip comments.
            line = re.sub(r"^#.*|\s#.*", "", line_content)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r"\s+", "", line))
    return sorted(requirements)


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, *args)


setup(
    name=NAME,
    author="Adam Twardoch",
    author_email="adam+github@twardoch.com",
    url=f"https://twardoch.github.io/{NAME}/",
    project_urls={"Source": f"https://github.com/twardoch/{NAME}/"},
    version=get_version(),
    license="MIT",
    description="Automagically generate thumbnails, animated GIFs, and summaries from videos (on macOS)",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    install_requires=get_requirements("requirements.txt"),
    extras_require={"dev": ["twine>=3.2.0"]},
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="macos screenshot video computer-vision thumbnails frames video-summarization animated-gifs macosx video-thumbnail gif-maker generating-thumbnails thumbnail-images macos-app video-thumbnail-generator gif-thumbnail shot-boundary-detection video-summaries hecate extracting-key-frames gui",
    entry_points="""
        [console_scripts]
        pyhecate=pyhecate.__main__:main
        """,
)
