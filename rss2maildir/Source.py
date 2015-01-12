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
import logging
import re


from io import BytesIO
from lxml import etree
import urllib
import socket
import http.client

log = logging.getLogger('rss2maildir:FeedSource')


class RawSource(object):
#    def _open_url(self, url, headers={}):
#        headers['User-agent'] = 'Mozilla/5.0'
#
#        try:
#            req = urllib.request.Request(url, headers=headers)
#            res = urllib.request.urlopen(req)
#            if url != res.geturl():
#                log.warning("redirected to '%s'" % res.geturl())
#            return res
#
#        except urllib.error.HTTPError as err:
#            log.warning('http request failed: %s' % str(err))
#            return None


    # NOTE: asymptotia.com returns "403 Bad Behavior" with urllib, because of the
    # header "Connection: close". I can't get rid of this, so I use rss2maildir's
    # own HTTP function.


    def _open_url(self, url, headers = {}):
        timeout=20
        max_redirects = 6
        redirect_on_status = (301, 302, 303, 307)
        log = logging.getLogger('GET %s' % url)

        urlold = url
        redirectcount = 0
        while redirectcount < max_redirects:

            try:
                (prot, rest) = urllib.parse.splittype(url)
                (host, path) = urllib.parse.splithost(rest)
                (host, port) = urllib.parse.splitport(host)

            except Exception as e:
                log.warning("url parsing failed: %s. %s (%s)" % (str(e), url, urlold))
                return None

            if prot == "https":
                if port == None:
                    port = 443
            else:
                if port == None:
                    port = 80

            try:
                if prot == "http":
                    conn = http.client.HTTPConnection("%s:%s" %(host, port), timeout=timeout)
                else:
                    conn = http.client.HTTPSConnection("%s:%s" %(host, port), timeout=timeout)
                conn.request('GET', path, headers=headers)
                response = conn.getresponse()

            except (http.client.HTTPException, socket.error) as e:
                log.warning('http request failed: %s (%s)' % (str(e), urlold))
                return None

            if response.status == 200:
                if urlold != url:
                    log.warning("redirected to '%s'" % url)
                return response

            elif response.status in redirect_on_status:
                response_headers = response.getheaders()
                for h in response_headers:
                    if h[0].lower() == "location":
                        newurl = h[1]

                        # detect relative paths
                        if re.match('/.*', newurl): newurl = '%s://%s%s' % (prot, host, path)

                        if url != newurl:
                            url = newurl
                        else:
                            return response

            else:
                log.warning('http error: %i %s (%s)' % (response.status, response.reason, urlold))
                return None

            redirectcount = redirectcount + 1

        log.warning('Maximum number of redirections reached (%s)' % urlold)
        return None

    def raw_data(url):
        return self._open_url(url)



class FeedSource(RawSource):
    """Fetches feeds directly from the url"""
    def __init__(self):
        # cached url and response and parsed stuff
        self.feed = {}


    def _parse_stream(self, url, stream):
        try:
             return feedparser.parse(stream)
        except Exception:
            log.warning("Can't parse feed %s" % url)
            return None


    def parse_feed(self, url):
        """parses feed, caches the parsed data, and returns the feed details"""
        # if the url is the same, return the cached feed
        if not url in self.feed:
            response = self._open_url(url)
            if not response: return None

            parsed_feed = self._parse_stream(url, response)
            if not parsed_feed: return None

            self.feed[url] = parsed_feed
        return self.feed[url]['feed']


    def parse_items(self, url):
        """generator that runs over parsed items"""
        if not url in self.feed:
            response = self._open_url(url)
            if not response: return

            parsed_feed = self._parse_stream(url, response)
            if not parsed_feed: return

            self.feed[url] = parsed_feed

        for item in self.feed[url]['items']:
            yield item



class FeedCachedSource(FeedSource):
    """Fetches feeds cached throgh google reader"""
    def __init__(self, max_cached=100):
        super().__init__()
        self.auth = None
        self.max_cached = max_cached


    def authenticate(self, user, password):
        res = urllib.request.urlopen("https://www.google.com/accounts/ClientLogin" + \
                                     "?service=reader&Email=%s&Passwd=%s" % (user, password))
        raw = res.read()
        self.auth = re.search(b'Auth=(.*)$', raw).group(1).decode('utf-8')


    def _process_feed(self, url, xml):
        """Recovers ids from the original feed, instead of the reader ids.
           Returns the continuation string, to keep fetching."""
        ns = {"atom": "http://www.w3.org/2005/Atom",
                "gr": "http://www.google.com/schemas/reader/atom/"}
        idkey = '{http://www.google.com/schemas/reader/atom/}original-id'

        for entry in xml.xpath('//atom:feed/atom:entry', namespaces = ns):
            # recover the original ID
            for it in entry.xpath('./atom:id', namespaces = ns):
                if idkey in it.attrib:
                    it.text = it.attrib[idkey]
                    del it.attrib[idkey]

            # get rid of greader specific categories
            for it in entry.xpath('./atom:category', namespaces = ns):
                if 'scheme' in it.attrib and it.attrib['scheme'] == "http://www.google.com/reader/":
                    entry.remove(it)

            # move <link rel=canonical> to <link rel=alternate>
            for it in entry.xpath('./atom:link', namespaces = ns):
                link_can = link_alt = None
                if it.attrib['rel'] == 'canonical': link_can = it
                if it.attrib['rel'] == 'alternate': link_alt = it

            if link_can != None and link_alt != None and 'href' in link_can.attrib:
                link_alt.attrib['href'] = link_can.attrib['href']

        for it in xml.xpath('//atom:feed/gr:continuation', namespaces = ns):
            return it.text


    def parse_items(self, url):
        """generator that parses over items"""
        headers = {'User-agent': 'Mozilla/5.0'}
        baseurl = "http://www.google.com/reader/atom/feed"
        if not self.auth:
            log.error("feed cache is not authenticated")
            return

        headers = {'Authorization': 'GoogleLogin auth=' + self.auth}

        count = 0
        continuation = None
        while count < self.max_cached:
            num = min(self.max_cached - count, 100)
            urlq = urllib.parse.quote(url)
            if continuation: cache_url = '%s/%s?r=n&n=%d&c=%s' % (baseurl, urlq, num, continuation)
            else:            cache_url = '%s/%s?r=n&n=%d' % (baseurl, urlq, num)

            response = self._open_url(cache_url, headers=headers)
            if not response: return

            xml = etree.parse(response)
            continuation = self._process_feed(url, xml)

            # Ideally I should be able to pass the xml tree to feedparser... oh well.
            parsed_feed = self._parse_stream(url, BytesIO(etree.tostring(xml)))
            if not parsed_feed: return

            for item in parsed_feed['items']:
                yield item
                count += 1

            if not continuation: break
