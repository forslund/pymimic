#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

setup(name='pymimic',
      version='0.4-dev0',
      packages = find_packages(),
      scripts = [os.path.join('bin', 'mimic_make_lex')],
      include_package_data=True,
      description='Python wrapper for mimic',
      author='Åke Forslund',
      author_email='ake.forslund@gmail.com',
      url='https://github.com/forslund/pymimic',
      download_url='https://github.com/forslund/pymimic/archive/0.4-dev0.tar.gz',
      keywords=['tts', 'text to speech'],
      )
