#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
import re

from setuptools import setup
from setuptools import find_packages


def get_version():
    VERSIONFILE = 'sentry_autogun/__init__.py'
    initfile_lines = open(VERSIONFILE, 'rt').readlines()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in initfile_lines:
        mo = re.search(VSRE, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version string in %s.' % (VERSIONFILE,))


install_requires = [
    'sentry>=4.9.8',
    'pyredmine'
]

setup(
    name='sentry-autogun',
    version=get_version(),
    author='Geoffrey Lehée',
    author_email='hello@socketubs.org',
    url='https://github.com/socketubs/sentry-autogun',
    description='A Sentry extension which integrates with Redmine.',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    zip_safe=False,
    install_requires=install_requires,
    include_package_data=True,
    entry_points={
        'sentry.apps': ['redmine = sentry_autogun'],
        'sentry.plugins': ['redmine = sentry_autogun.plugin:AutogunPlugin']},
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
