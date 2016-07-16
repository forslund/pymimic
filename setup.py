#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup
from distutils.command.install import install as DistutilsInstall
from distutils.command.build import build
from subprocess import call
import os


BASEPATH = os.path.dirname(os.path.abspath(__file__))
MIMICPATH = os.path.join(BASEPATH, 'mimic')


class PyMimicBuild(build):
    def run(self):
        # Run original build code
        build.run(self)

        # build mimic
        build_path = os.path.abspath(self.build_temp)
        configure_cmd = [
            './configure',
            '--prefix=' + build_path,
            '--disable-voices-all',
            '--with-audio=none',
            '--enable-shared']
        make_cmd = ['make']
        make_install_cmd = ['make', 'install']

        def configure():
            call(configure_cmd, cwd=MIMICPATH)

        def make():
            call(make_cmd, cwd=MIMICPATH)
            call(make_install_cmd, cwd=MIMICPATH)
        self.execute(configure, [], 'Configuring Mimic')
        self.execute(make, [], 'Building mimic')

        # copy so-files
        lib_path = build_path + '/lib/'
        target_files = [lib_path + 'libmimic.so',
                        lib_path + 'libmimic_lang_usenglish.so',
                        lib_path + 'libmimic_lang_cmulex.so',
                        'pymimic/pymimic.py']

        self.mkpath(self.build_lib)
        if not self.dry_run:
            for target in target_files:
                self.copy_file(target, self.build_lib)


class PyMimicInstall(DistutilsInstall):
    def initialize_options(self):
        DistutilsInstall.initialize_options(self)
        self.build_scripts = None

    def finalize_options(self):
        DistutilsInstall.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        # run original install code
        DistutilsInstall.run(self)

        self.copy_tree(self.build_lib, self.install_lib)


setup(name='pymimic',
      version='0.1',
      description='Python wrapper for mimic',
      author='Åke Forslund',
      author_email='ake.forslund@gmail.com',
      url='https://github.com/forslund',
      download_url='https://github.com/forslund/pymimic/tarball/0.1',
      keywords=['tts', 'text to speach'],
      classifiers=[],
      cmdclass={'build': PyMimicBuild,
                'install': PyMimicInstall}
      )
