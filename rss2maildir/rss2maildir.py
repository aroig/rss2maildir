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
import logging
import imp
import sys
import traceback
import netrc
import urllib

from multiprocessing.pool import ThreadPool

from .Source import FeedCachedSource, FeedSource
from .Maildir import Maildir
from .Feed import Feed
from .Settings import FeedConfig


log = logging.getLogger('rss2maildir')



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


class myLogFormatter(logging.Formatter):
    def __init__(self):
        return super(myLogFormatter, self).__init__('%(message)s')

    def format(self, record):
        if record.levelno == logging.INFO:
            return record.msg
        else:
            return '%s: %s' % (record.levelname, record.msg)



def fetch_feed(feed, maildir, dryrun=False):
    count = 0
    global item_count

    for item in feed.items():
        link = item.link
#        print(str(item))
#        continue

        # apply item filters
        for item_filter in feed.item_filters:
            item = item_filter(item)
            if not item: break
        if not item:
            log.warning("filtering out item: %s" % link)
            continue                   # the item is discarded

        item.compute_hashes()      # need to recompute hashes, as id's may have changed

        # if not new, skip
        if not maildir.new(item): continue

        count = count + 1
        # deliver item
        if not dryrun:
            maildir.deliver(item, html=feed.html)

    log.info("fetched items in '%s' [%d]" % (feed.name, count))
    item_count = item_count + count
    return count



def setup_logger(verbosity=0, logfile=None):
    loglevels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }

    # root logger
    rootlog = logging.getLogger('')
    rootlog.setLevel(logging.DEBUG)

    # setup logging the console
    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(loglevels[min(2, verbosity)])
    console.setFormatter(myLogFormatter())
    rootlog.addHandler(console)

    # setup logging to a logfile
    if logfile:
        filelogger = logging.FileHandler(logfile, 'w')
        filelogger.setLevel(logging.INFO)
        filelogger.setFormatter(
            logging.Formatter(fmt = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                              datefmt = '%Y-%m-%d %H:%M'))
        rootlog.addHandler(filelogger)



def prepare_feed_list(settings, maildir, filter_feeds=None, max_items=100):
    feed_list = []

    # feed sources. implement the download and parsing machinery
    cached_source = FeedCachedSource()
    raw_source = FeedSource()

    # maildir config
    maildir_template = settings['maildir_template']

    for url in settings.feeds():

        # setup feed source
        if settings.getboolean(url, 'cached'): feed_source = cached_source
        else:                                  feed_source = raw_source

        # max items
        max_items=int(settings.get(url, 'max_cached'))

        # get config data
        name = urllib.parse.urlencode((('', url), )).split("=")[1]
        if settings.has_option(url, 'name'):
            name = settings.get(url, 'name')

        relative_maildir = maildir_template.replace('{}', name)
        if settings.has_option(url, 'maildir'):
            relative_maildir = settings.get(url, 'maildir')

        # get list of keywords
        keywords = sorted(settings.getlist(url, 'keywords'))

        # filter feeds if passed arguments
        if filter_feeds and not relative_maildir in filter_feeds:
            continue

        # make sure a maildir for feed exists
        try:
            maildir.create(relative_maildir)
        except OSError as e:
            log.warning('Could not create maildir %s: %s' % (relative_maildir, str(e)))
            log.warning('Skipping feed %s' % url)

        # load item filters
        item_filters = [getattr(settings.filters, ft) for ft in settings.getlist(url, 'filters')]

        feed = Feed(url, name, relative_maildir, feed_source,
                    keywords = keywords,
                    item_filters = item_filters,
                    html = settings.getboolean(url, 'html'),
                    max_cached = max_items)

        feed_list.append(feed)

    return feed_list



def dedup(opts, args):
    cfgdir = opts.conf or os.path.realpath(os.path.expanduser('~/.config/rss2maildir'))

    # settings
    settings = FeedConfig(cfgdir)

    # setup the logging
    setup_logger(verbosity=opts.verbosity, logfile=opts.logfile)

    maildir = Maildir(settings['maildir_root'])
    maildir.dedup(dryrun=opts.dryrun)



# stores exception data from the threads
exc_info = None
item_count = 0

def main(opts, args):
    cfgdir = opts.conf or os.path.realpath(os.path.expanduser('~/.config/rss2maildir'))

    # setup the logging
    setup_logger(verbosity=opts.verbosity, logfile=opts.logfile)

    # config
    settings = FeedConfig(cfgdir)
    num_threads = int(settings['threads'])

    # select specific feeds
    if len(args) > 0: filter_feeds = set(args)
    else:             filter_feeds = None

    # TODO: Authenticate to a cached source if needed

    # root maildir
    maildir = Maildir(settings['maildir_root'])

    # generate feed list
    feed_list = prepare_feed_list(settings, maildir, filter_feeds=filter_feeds)
    print(feed_list)
    sys.exit(1)

    global item_count
    item_count = 0
    if num_threads > 1:
        pool = ThreadPool(num_threads)
        def fetch_feed_closure(f):
            try:
                fetch_feed(f, maildir, dryrun=opts.dryrun)
            # store first exception data to be collected in the main thread
            except Exception as e:
                global exc_info
                import sys
                if not exc_info: exc_info = sys.exc_info()

        log.info("fetching feeds (%d threads)" % num_threads)
        global exc_info
        res = pool.map_async(fetch_feed_closure, feed_list, chunksize=1)
        while not res.ready():
            res.wait(1)
            if exc_info:
                raise ThreadException(exc_info[0], exc_info[1], exc_info[2])
        pool.terminate()
    else:
        log.info("fetching feeds (single threaded)")
        for feed in feed_list:
            fetch_feed(feed, maildir)

    log.info("%d items downloaded" % item_count)
