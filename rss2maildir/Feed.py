# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
#
# Copyright (C) 2007  Brett Parker <iDunno@sommitrealweird.co.uk>
# Copyright (C) 2011  Justus Winter <4winter@informatik.uni-hamburg.de>
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

from .Item import Item
from .utils import open_url, generate_random_string

log = logging.getLogger('rss2maildir:Feed')

class Feed(object):
    def __init__(self, url, name, maildir, keywords=[]):
        self.url = url
        self.name = name
        self.keywords = set(keywords)
        self.maildir = maildir
        self.response = None


    def new_items(self, maildir):
        self.response = open_url('GET', self.url)
        if not self.response:
            log.warning('Fetching feed %s failed' % (self.url))
            return

        parsed_feed = feedparser.parse(self.response)
        for item in (Item(self, feed_item) for feed_item in parsed_feed['items']):
            if maildir.seen(item):
                log.info('Item %s already seen, skipping' % item.link)
                continue
            yield item
