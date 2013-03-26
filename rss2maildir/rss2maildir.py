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
import sys
import traceback

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


class ThreadException(Exception):
    def __init__(self, type, value, traceback):
        super(ThreadException, self).__init__("Exception in a thread")
        self.thread_traceback = traceback
        self.thread_value = value
        self.thread_type = type

    def __str__(self):
        exception_rep = traceback.format_exception(self.thread_type, self.thread_value, self.thread_traceback)
        return "%s\n%s" % (super(ThreadException, self).__str__(),
                           ''.join(exception_rep))


# stores exception data from the threads
exc_info = None
item_count = 0

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
        name = urllib.parse.urlencode((('', url), )).split("=")[1]
        if settings.has_option(url, 'name'):
            name = settings.get(url, 'name')

        relative_maildir = maildir_template.replace('{}', name)
        if settings.has_option(url, 'maildir'):
            relative_maildir = settings.get(url, 'maildir')

        # get list of keywords
        keywords = sorted(settings.getlist(url, 'keywords'))

        # make sure a maildir for feed exists
        try:
            maildir.create(relative_maildir)
        except OSError as e:
            log.warning('Could not create maildir %s: %s' % (relative_maildir, str(e)))
            log.warning('Skipping feed %s' % url)

        # load item filters
        item_filters = [getattr(settings.filters, ft) for ft in settings.getlist(url, 'filters')]

        # message format settings
        html = settings.getboolean(url, 'html')

        feed = Feed(url, name, relative_maildir, keywords=keywords, item_filters=item_filters, html=html)
        feed_list.append(feed)

    global item_count
    item_count = 0
    if num_threads > 1:
        pool = ThreadPool(num_threads)
        def fetch_feed_closure(f):
            try:
                fetch_feed(f, maildir)
            # store first exception data to be collected in the main thread
            except Exception as e:
                global exc_info
                import sys
                if not exc_info: exc_info = sys.exc_info()

        global exc_info
        res = pool.map_async(fetch_feed_closure, feed_list, chunksize=1)
        while not res.ready():
            res.wait(1)
            if exc_info:
                raise ThreadException(exc_info[0], exc_info[1], exc_info[2])
        pool.terminate()
    else:
        print("Threading disabled")
        for feed in feed_list:
            fetch_feed(feed, maildir)

    print("%d items downloaded" % item_count)

def fetch_feed(feed, maildir):
    print("fetching items in '%s'" % feed.name)
    count = 0
    global item_count

    for item in feed.items():
#        print(str(item))
#        continue
        if not maildir.new(item): continue

        # apply item filters
        for item_filter in feed.item_filters:
            item = item_filter(item)
            if not item: break
        if not item: continue

        count = count + 1
        # deliver item
        maildir.deliver(item, html=feed.html)

    item_count = item_count + count
    return count
