# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
#
# Copyright (C) 2007  Brett Parker <iDunno@sommitrealweird.co.uk>
# Copyright (C) 2011  Justus Winter <4winter@informatik.uni-hamburg.de>
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

import logging
import feedparser
import datetime
import urllib

from .Item import Item
from .utils import open_url, generate_random_string

log = logging.getLogger('rss2maildir:Feed')

class Feed(object):
    def __init__(self, url, name, maildir, keywords=[], item_filters=[], html=True, cache=None):
        self.url = url
        self.name = name.strip()
        self.keywords = set(keywords)
        self.item_filters = item_filters
        self.html = html
        self.maildir = maildir.strip()
        self.cache = cache


    def _open_feed(self, url):
        try:
            headers = {'User-agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)

            if self.cache: return self.cache.open_feed(url)
            else:          return urllib.request.urlopen(req)

        except urllib.error.HTTPError as err:
            log.warning('http request failed: %s' % str(err))
            return None



    def items(self):
        response = self._open_feed(self.url)
        if not response:
            log.warning('Fetching feed %s failed' % (self.url))
            return

        try:
            parsed_feed = feedparser.parse(response)

        except Exception as e:
            log.warning('Parsing feed %s failed' % (self.url))
            return

        self.updateddate = datetime.datetime.now()
        try:
            self.updateddate = datetime.datetime(*(parsed_feed['feed']['published_parsed'][0:6]))
        except Exception as e:
            pass

        try:
            self.updateddate = datetime.datetime(*(parsed_feed['feed']['updated_parsed'][0:6]))
        except Exception as e:
            pass

        for feed_item in parsed_feed['items']:
            yield Item(self, feed_item)


    def new_items(self, maildir):
        for item in self.items():
            if maildir.seen(item):
                log.info('Item %s already seen, skipping' % item.link)
                continue
            yield item
