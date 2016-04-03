# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
# Copyright (C) 2015  Abdó Roig-Maranges <abdo.roig@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import hashlib


class Webcache(object):
    def __init__(self, path):
        self.path = os.path.realpath(os.path.expanduser(path))

    def _hash(self, url):
        return hashlib.sha1(url.encode('utf-8')).hexdigest()

    def update(self, url, content):
        md5 = self._hash(url)
        with open(os.path.join(self.path, md5), 'w') as fd:
            fd.write(content)

    def has_url(self, url):
        md5 = self._hash(url)
        return os.path.exists(os.path.join(self.path, md5))

    def get(self, url):
        md5 = self._hash(url)
        if os.path.exists(os.path.join(self.path, md5)):
            with open(os.path.join(self.path, md5), 'r') as fd:
                data = fd.read()
        else:
            data = ''

        return data
