# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
#
# Copyright (C) 2013  Abdó Roig-Maranges <abdo.roig@gmail.com>
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

import urllib
import logging
import re

log = logging.getLogger('rss2maildir:FeedCache')


class FeedCache(object):
    def __init__(self, max_items=100):
        self.max_items = max_items
        self.auth = None


    def authenticate(self, user, password):
        res = urllib.request.urlopen("https://www.google.com/accounts/ClientLogin?service=reader&Email=%s&Passwd=%s" % (user, password))
        raw = res.read()
        self.auth = re.search(b'Auth=(.*)$', raw).group(1).decode('utf-8')


    def open_feed(self, url):
        cache_url = 'http://google.com/reader/atom/feed/%s?r=n&n=%d' % \
                    (url, self.max_items)

        headers = {'User-agent': 'Mozilla/5.0'}
        if self.auth:
            headers['Authorization'] = 'GoogleLogin auth=' + self.auth
            req = urllib.request.Request(cache_url, headers=headers)
        else:
            req = urllib.request.Request(url, headers=headers)

        return urllib.request.urlopen(req)
