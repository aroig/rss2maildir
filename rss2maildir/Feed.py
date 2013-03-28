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

from .Item import Item
from .utils import generate_random_string

log = logging.getLogger('rss2maildir:Feed')

class Feed(object):
    def __init__(self, url, name, maildir, source, keywords=[], item_filters=[], html=True, max_cached=100):
        self.url = url
        self.name = name.strip()
        self.keywords = set(keywords)
        self.item_filters = item_filters
        self.html = html
        self.maildir = maildir.strip()
        self.source = source
        self.updateddate = None
        self.max_cached = max_cached

    def _get_updateddate(self, parsed_feed):
        self.updateddate = datetime.datetime.now()
        try:
            self.updateddate = datetime.datetime(*(parsed_feed['published_parsed'][0:6]))
        except Exception as e:
            pass

        try:
            self.updateddate = datetime.datetime(*(parsed_feed['updated_parsed'][0:6]))
        except Exception as e:
            pass


    def items(self):
        parsed_feed = self.source.parse_feed(self.url)
        if not parsed_feed: return

        # get the updated date for the feed
        self._get_updateddate(parsed_feed)

        count = 0
        for feed_item in self.source.parse_items(self.url, self.max_cached):
            yield Item(self, feed_item)
            count += 1

        if count == 0: log.warning("empty parsed feed: %s" % self.url)


    def new_items(self, maildir):
        for item in self.items():
            if maildir.seen(item):
                log.info('Item %s already seen, skipping' % item.link)
                continue
            yield item
