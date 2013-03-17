# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
# Copyright (C) 2007  Brett Parker <iDunno@sommitrealweird.co.uk>
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

import os
import urllib
import logging
import imp

from multiprocessing.pool import ThreadPool

from .Maildir import Maildir
from .Feed import Feed
from .Settings import FeedConfig


log = logging.getLogger('rss2maildir')

loglevels = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


# stores exception data from the threads
exc_info = None


def main(opts, args):
    cfgdir = opts.conf or os.path.realpath(os.path.expanduser('~/.config/rss2maildir'))
    settings = FeedConfig(cfgdir)
    logging.basicConfig(level = loglevels[min(2, opts.verbosity)])

    maildir_template = settings['maildir_template']
    maildir = Maildir(settings['maildir_root'])

    num_threads = int(settings['threads'])

    feed_list = []
    for url in settings.feeds():
        # get config data
        name = urllib.urlencode((('', url), )).split("=")[1]
        if settings.has_option(url, 'name'):
            name = settings.get(url, 'name')

        relative_maildir = maildir_template.replace('{}', name)
        if settings.has_option(url, 'maildir'):
            relative_maildir = settings.get(url, 'maildir')

        keywords = []
        if settings.has_option(url, 'keywords'):
            keywords = sorted([k.strip() for k in settings.get(url, 'keywords').split(',')])

        # make sure a maildir for feed exists
        try:
            maildir.create(relative_maildir)
        except OSError as e:
            log.warning('Could not create maildir %s: %s' % (relative_maildir, str(e)))
            log.warning('Skipping feed %s' % url)

        # load item filters
        item_filters = None
        if settings.has_option(url, 'filters'):
            item_filters_raw = [ft.strip() for ft in settings.get(url, 'filters').split(',')]
            item_filters = [getattr(settings.filters, ft) for ft in item_filters_raw]

        # message format settings
        html = settings.getboolean(url, 'html')

        feed = Feed(url, name, relative_maildir, keywords=keywords, item_filters=item_filters, html=html)
        feed_list.append(feed)

    pool = ThreadPool(num_threads)
    def fetch_feed_closure(f):
        try:
            fetch_feed(f, maildir)
        # store first exception data to be collected in the main thread
        except Exception, e:
            global exc_info
            import sys
            if not exc_info: exc_info = sys.exc_info()

    global exc_info
    res = pool.map_async(fetch_feed_closure, feed_list, chunksize=1)
    while not res.ready():
        res.wait(0)
        if exc_info: raise exc_info[1], None, exc_info[2]
    pool.terminate()


def fetch_feed(feed, maildir):
    print("fetching items in '%s'" % feed.name)
    for item in feed.new_items(maildir):
        # apply item filters
        if feed.item_filters:
            for item_filter in feed.item_filters:
                item = item_filter(item)
                if not item: break
        if not item: break

        # deliver item
        maildir.deliver(item, html=feed.html)
