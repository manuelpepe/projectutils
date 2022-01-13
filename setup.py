#!/usr/bin/env python
from pathlib import Path
from distutils.core import setup

README = Path(__file__).parent / "README.md"
with open(README) as fp:
    long_description = fp.read()

setup(
    name="projectutils",
    version="1.1",
    description="A small collections of modular components useful in other projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Manuel Pepe",
    author_email="manuelpepe-dev@outlook.com.ar",
    url="https://github.com/manuelpepe/projectutils",
    include_package_data=True,
    packages=["projectutils"],
    install_requires=["python-dotenv", "rst==0.1"],
    extras_require={"toml": ["toml"]},
)
