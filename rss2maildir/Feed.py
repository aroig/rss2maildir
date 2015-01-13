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

from .Item import RssItem, WebItem
from .utils import generate_random_string

log = logging.getLogger('rss2maildir:Feed')


class FeedBase(object):
    def __init__(self, conf, source):
        self.url = conf['url']
        self.name = conf['name'].strip()
        self.keywords = set(conf['keywords'])
        self.item_filters = conf['item_filters']
        self.html = conf['html']
        self.maildir = conf['maildir'].strip()

        self.source = source
        self.updateddate = None

    def _get_updateddate(self, parsed_feed):
        self.updateddate = datetime.datetime.now()

    def apply_filters(self, item):
        for item_filter in self.item_filters:
            item = item_filter(item)
            if not item: break

        if item:
            item.compute_hashes()

        return item



class RssFeed(FeedBase):
    def __init__(self, conf, source):
        super(RssFeed, self).__init__(conf, source)

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
        for feed_item in self.source.parse_items(self.url):
            item = RssItem(self, feed_item)
            yield item
            count += 1

        if count == 0: log.warning("empty parsed feed: %s" % self.url)

    def filtered_items(self):
        for item in self.items():
            link = item.link

            item = self.apply_filters(item)
            if not item:
                log.warning("filtering out item: %s" % link)
            else:
                yield item



class WebFeed(FeedBase):
    def __init__(self, conf, source, cache):
        super(WebFeed, self).__init__(conf, source)
        self.cache = cache

    # TODO:
    # 1. get raw data
    # 2. make diff with cache
    # 3. generate item
    # 4. update cache


    def items(self):
        return
        raw = self.source.raw_data(self.url)

        # TODO: compute diff
        diff = None

        if diff:
            content= "blah"
            id = "blah"
            item = WebItem(self, {'content': content, 'id': id})
            yield item

        else:
            return

    def filtered_items(self):
        for item in self.items():
            yield item
