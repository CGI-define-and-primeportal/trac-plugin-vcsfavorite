from setuptools import setup

setup(
    name = 'VCSFavoritePlugin',
    version = '0.1',
    author = 'Mikael Svensson',
    author_email = 'm.svensson@cgi.com',
    description = 'Version control system favorites.',
    license = \
    """Copyright (c) 2013, CGI. All rights reserved. Released under the 3-clause BSD license. """,
    packages = ['vcsfavoriteplugin',
                'vcsfavoriteplugin.upgrades'],
    package_data = {'vcsfavoriteplugin': [
        'templates/*.html',
        'htdocs/js/*.js',
        'htdocs/css/*.css',
        'htdocs/*.png']
    },
    entry_points = {
        'trac.plugins': [
            'vcsfavoriteplugin.api = vcsfavoriteplugin.api',
            ]},
    install_requires = ['Trac>=0.12', 'Genshi>=0.5',],
)
