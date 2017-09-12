#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

setup(name='pymimic',
      version='0.3-dev',
      packages = find_packages(),
      scripts = [os.path.join('bin', 'mimic_huff_table'), 
                 os.path.join('bin', 'mimic_make_lex'),
                 os.path.join('bin', 'mimic_lts_train.py'),
                 os.path.join('bin', 'make_lex.scm')],
      description='Python wrapper for mimic',
      author='Åke Forslund',
      author_email='ake.forslund@gmail.com',
      url='https://github.com/forslund/pymimic',
      download_url='https://github.com/forslund/pymimic/archive/0.1.1dev.tar.gz',
      keywords=['tts', 'text to speech'],
      )
