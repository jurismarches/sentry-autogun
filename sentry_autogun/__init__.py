# ~*~ coding: utf-8 ~*~
"""
sentry_autogun
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2013 by Geoffrey Lehée
:license: BSD, see LICENSE for more details.
"""

try:
    VERSION = __import__('pkg_resources') \
        .get_distribution('sentry-autogun').version
except Exception, e:
    VERSION = 'unknown'
