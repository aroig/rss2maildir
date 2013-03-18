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

import re
import os
import socket
import datetime
import logging

from .utils import make_maildir

log = logging.getLogger('rss2maildir:Maildir')

class Maildir(object):
    def __init__(self, path):
        self.path = os.path.expanduser(path)
        self.data = {}

        # load messages
        for mp in self.messages():
            self.updatepath(mp)

        # clean tmp dirs
        for md in os.listdir(self.path):
            p = os.path.join(self.path, md)
            if os.path.isdir(p):
                for ms in os.listdir(p):
                    p = os.path.join(self.path, md, 'tmp', ms)
                    if os.path.isfile(p):
                        log.info("Cleaning file in tmp: %s" % p)
                        os.unlink(p)


    def messages(self):
        for md in os.listdir(self.path):
            p = os.path.join(self.path, md)
            if os.path.isdir(p):
                for st in ['cur', 'new']:
                    p = os.path.join(self.path, md, st)
                    for ms in os.listdir(p):
                        p = os.path.join(self.path, md, st, ms)
                        if os.path.isfile(p):
                            yield p


    def updatepath(self, path):
        m = self.path2metadata(path)
        if not m:
            log.warning("Can't parse filename: %s" % path)
            return

        maildir = m['maildir']
        md5 = m['md5']
        if not maildir in self.data: self.data[maildir] = {}
        self.data[maildir][md5] = m


    def filename(self, item):
        return '%i.%s.%s.%s' % (os.getpid(),
                                socket.gethostname(),
                                item.md5sum,
                                item.createddate.strftime('%s'))


    def path2metadata(self, path):
        directory, name = os.path.split(path)
        directory, state = os.path.split(directory)
        maildir = os.path.basename(directory)
        m = re.match('^(.*?)\.(.*?)\.(.*?)\.([0-9]*?)(:.*)?$', name)

        if m:
            return {'md5': m.group(3).encode('utf-8'),
                    'created': datetime.datetime.fromtimestamp(int(m.group(4))),
                    'maildir': maildir.encode('utf-8'),
                    'state': state.encode('utf-8'),
                    'path': path.encode('utf-8')}
        else:
            return None


    def create(self, maildir):
        maildir_full = os.path.join(self.path, maildir)
        make_maildir(maildir_full)


    def deliver(self, item, html=True):
        file_name = self.filename(item)
        maildir = item.feed.maildir
        message = item.create_message(html = html)
        if not message: return

        maildir_full = os.path.join(self.path, maildir)

        # store message in tmp
        tmp_path = os.path.join(maildir_full, 'tmp', file_name)
        handle = open(tmp_path, 'w')
        handle.write(message.as_string())
        handle.close()

        # now move it in to the new directory
        new_path = os.path.join(maildir_full, 'new', file_name)
        if os.path.exists(new_path):
            os.unlink(new_path)
        os.link(tmp_path, new_path)
        os.unlink(tmp_path)

        # update data dictionary
        self.updatepath(new_path)



    def seen(self, item):
        maildir = item.feed.maildir
        return maildir in self.data and item.md5sum in self.data[maildir]
