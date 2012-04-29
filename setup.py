#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = 'dcpu16',
    version = '1.0',
    description = 'dcpu16 Compiler',
    author = 'Jozef Leskovec',
    author_email = 'jozefleskovec@gmail.com',
    packages = find_packages(exclude = ["tests"]),
    install_requires = ['argparse', 'ply'],
)
