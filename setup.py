#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~
"""
sentry-autogun
==============

An extension for Sentry which integrates with Redmine. Specifically, it allows you to ...

:copyright: (c) 2013 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from setuptools import setup, find_packages


tests_require = [
    'nose',
]

install_requires = [
    'sentry>=4.9.8',
    'pyredmine'
]

setup(
    name='sentry-autogun',
    version='0.1.3',
    author='Geoffrey Lehée',
    author_email='geoffrey@lehee.name',
    url='http://github.com/socketubs/sentry-autogun',
    description='A Sentry extension which integrates with Redmine.',
    long_description=__doc__,
    license='BSD',
    packages=find_packages(exclude=['tests']),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={'test': tests_require},
    test_suite='runtests.runtests',
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
