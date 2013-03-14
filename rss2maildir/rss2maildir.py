# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
# Copyright (C) 2007  Brett Parker <iDunno@sommitrealweird.co.uk>
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

from .Database import Database
from .Feed import Feed
from .Settings import FeedConfig
from .utils import make_maildir

log = logging.getLogger('rss2maildir')

loglevels = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


def main(opts, args):
    cfgdir = opts.conf or os.path.realpath(os.path.expanduser('~/.config/rss2maildir'))
    settings = FeedConfig(cfgdir)
    logging.basicConfig(level = loglevels[min(2, opts.verbosity)])

    database = Database(os.path.expanduser(settings['state_dir']))

    for url in settings.feeds():
        if settings.has_option(url, 'name'):
            name = settings.get(url, 'name')
        else:
            name = urllib.urlencode((('', url), )).split("=")[1]

        if settings.has_option(url, 'maildir'):
            relative_maildir = settings.get(url, 'maildir')
        else:
            relative_maildir = settings.get(url, 'maildir_template').replace('{}', name)

        keywords = []
        if settings.has_option(url, 'keywords'):
            keywords = sorted([k.strip() for k in settings.get(url, 'keywords').split(',')])

        maildir = os.path.join(os.path.expanduser(settings['maildir_root']), relative_maildir)

        try:
            make_maildir(maildir)
        except OSError as e:
            log.warning('Could not create maildir %s: %s' % (maildir, str(e)))
            log.warning('Skipping feed %s' % url)
            continue

        # get item filters
        item_filters = None
        if settings.has_option(url, 'item_filters'):
            item_filters_raw = [ft.strip() for ft in settings.get(url, 'item_filters').split(',')]
            item_filters = [getattr(settings.filters, ft) for ft in item_filters_raw]

        include_html_part=settings.getboolean(url, 'include_html_part')

        # right - we've got the directories, we've got the url, we know the
        # url... lets play!

        print("Fetching items in '%s'" % name)
        feed = Feed(database, url, name, keywords=keywords)
        for item in feed.new_items():
            message = item.create_message(
                include_html_part=include_html_part,
                item_filters=item_filters)
            if message:
                item.deliver(message, maildir)
