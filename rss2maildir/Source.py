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

import feedparser
import urllib
import logging
import re


from io import BytesIO
from lxml import etree


log = logging.getLogger('rss2maildir:FeedSource')


class FeedSource(object):
    """Fetches feeds directly from the url"""
    def __init__(self):
        # cached url and response and parsed stuff
        self.url = None
        self.feed = None
        self.items = None


    def _open_url(self, url, auth=None, headers={}):
        headers['User-agent'] = 'Mozilla/5.0'

        req = urllib.request.Request(url, headers=headers)
        try:
            res = urllib.request.urlopen(req)
            if url != res.geturl():
                log.warning("Redirected to '%s'" % res.geturl())
            return res

        except urllib.error.HTTPError as err:
            log.warning('http request failed: %s' % str(err))
            return None


    def _parse_stream(self, url, stream):
        try:
             return feedparser.parse(stream)
        except Exception:
            log.warning("Can't parse feed %s" % url)
            return None


    def parse_feed(self, url):
        """parses feed, caches the parsed data, and returns the feed details"""
        # if the url is the same, return the cached feed
        if url != self.url:
            self.url = url
            response = self._open_url(url)
            if not response: return None

            parsed_feed = self._parse_stream(url, response)
            if not parsed_feed: return None

            self.feed = parsed_feed['feed']
            self.items = parsed_feed['items']
        return self.feed


    def parse_items(self, url, max_cached=100):
        """generator that tund over parsed items"""
        if url != self.url:
            response = self._open_url(url)
            if not response: return

            parsed_feed = self._parse_stream(url, response)
            if not parsed_feed: return

            self.feed = parsed_feed['feed']
            self.items = parsed_feed['items']

        for item in self.items:
            yield item




class FeedCachedSource(FeedSource):
    """Fetches feeds cached throgh google reader"""
    def __init__(self):
        super().__init__()
        self.auth = None


    def authenticate(self, user, password):
        res = urllib.request.urlopen("https://www.google.com/accounts/ClientLogin" + \
                                     "?service=reader&Email=%s&Passwd=%s" % (user, password))
        raw = res.read()
        self.auth = re.search(b'Auth=(.*)$', raw).group(1).decode('utf-8')


    def _process_feed(self, xml):
        """Recovers ids from the original feed, instead of the reader ids.
           Returns the continuation string, to keep fetching."""
        ns = {"atom": "http://www.w3.org/2005/Atom",
                "gr": "http://www.google.com/schemas/reader/atom/"}
        idkey = '{http://www.google.com/schemas/reader/atom/}original-id'

        for entry in xml.xpath('//atom:feed/atom:entry', namespaces = ns):
            # recover the original ID
            for it in entry.xpath('./atom:id', namespaces = ns):
                it.text = it.attrib[idkey]
                del it.attrib[idkey]

            # get rid of greader specific categories
            for it in entry.xpath('./atom:category', namespaces = ns):
                if it.attrib['scheme'] == "http://www.google.com/reader/":
                    entry.remove(it)

            # move <link rel=canonical> to <link rel=alternate>
            for it in entry.xpath('./atom:link', namespaces = ns):
                if it.attrib['rel'] == 'canonical': link_can = it
                if it.attrib['rel'] == 'alternate': link_alt = it
            if link_can != None and link_alt != None:
                link_alt.attrib['href'] = link_can.attrib['href']

        for it in xml.xpath('//atom:feed/gr:continuation', namespaces = ns):
            return it.text


    def parse_items(self, url, max_cached=100):
        """generator that parses over items"""
        headers = {'User-agent': 'Mozilla/5.0'}
        baseurl = "http://www.google.com/reader/atom/feed"
        if not self.auth:
            log.error("feed cache is not authenticated")
            return

        headers = {'Authorization': 'GoogleLogin auth=' + self.auth}

        count = 0
        continuation = None
        while count < max_cached:
            num = min(max_cached - count, 100)
            if continuation: cache_url = '%s/%s?r=n&n=%d&c=%s' % (baseurl, url, num, continuation)
            else:            cache_url = '%s/%s?r=n&n=%d' % (baseurl, url, num)

            response = self._open_url(cache_url, headers=headers)
            if not response: return

            xml = etree.parse(response)
            continuation = self._process_feed(xml)

            # Ideally I should be able to pass the xml tree to feedparser... oh well.
            parsed_feed = self._parse_stream(url, BytesIO(etree.tostring(xml)))
            if not parsed_feed: return

            for item in parsed_feed['items']:
                yield item
                count += 1

            if not continuation: break
