#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import wheelsoup

setup(
        name             = 'wheelsoup',
        version          = wheelsoup.__version__,
        description      = wheelsoup.__doc__.strip(' \r\n'),
        license          = wheelsoup.__license__,
        author           = wheelsoup.__author__,
        author_email     = 'mailohmi@gmail.com',
        url              = 'https://mailohmi@bitbucket.org/mailohmi/logrec.git',
        keywords         = 'pip wheel',
        packages         = find_packages(),
        install_requires = ["wheel", "pip"],
        # script entry
        entry_points={
            'console_scripts': [
                'wheelsoup = wheelsoup.__main__:console_main'
            ]
        }
    )
