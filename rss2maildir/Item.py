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

import re
import os
import sys
import socket
import datetime
from .HTML2Text import HTML2Text
from .utils import generate_random_string, compute_hash

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import charset
from email.header import Header

import html.entities


# Default encoding mode set to Quoted Printable.
charset.add_charset('utf-8', charset.QP, charset.QP)

class ItemBase(object):
    def __init__(self, feed, feed_item):
        self.feed = None
        self.author = None
        self.title = None
        self.link = None
        self.keywords = set()
        self.content = ''
        self.id = None
        self.categories = set()
        self.createddate = None
        self.previous_message_id = None

    def _message_id(self):
        if self.id:
            raw = '%s.%s' % (self.feed.maildir, self.id)
        else:
            raw = '%s.%s' % (datetime.datetime.now().strftime("%Y%m%d%H%M"),
                             generate_random_string(6))

        return '<%s@rss2maildir>' % compute_hash(raw)

    def __getitem__(self, key):
        return getattr(self, key)

    def __str__(self):
        ret = ""
        ret = ret + "Title: %s\n" % self.title
        ret = ret + "Author: %s\n" % self.author
        ret = ret + "Keywords: %s\n" % ', '.join(self.keywords)
        ret = ret + "MD5: %s\n" % self.md5sum
        ret = ret + "ID: %s\n" % self.id
        ret = ret + "URL: %s\n" % self.link
        ret = ret + "Content:\n%s\n" % self.content
        return ret

    def compute_hashes(self):
        self.md5sum = compute_hash(self.content)

        if self.id:      self.md5id = compute_hash(self.id.strip())
        elif self.title: self.md5id = compute_hash(self.title.strip())
        else:            self.md5id = None

    def unescape_utf8_xml(self, text):
        def fixup(m):
            txt = m.group(0)
            if txt[:2] == "&#":
                # character reference
                try:
                    if txt[:3] == "&#x":
                        return chr(int(txt[3:-1], 16))
                    else:
                        return chr(int(txt[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    txt = chr(html.entities.name2codepoint[txt[1:-1]])
                except KeyError:
                    pass
            return txt # leave as is

        return re.sub("&#?[a-zA-Z0-9_]+;", fixup, text, flags=re.UNICODE)

    def create_message(self, html = True):
        item = self
        message = MIMEMultipart('alternative')

        header = Header()
        if item.author: header.append(item.author, 'utf-8')
        else:           header.append(item.feed.name, 'utf-8')
        header.append(" <rss2maildir@localhost>", 'ascii')
        message['From'] = header

        message['To'] = 'rss2maildir@localhost'

        header = Header()
        if item.title: title = item.title.replace('<', '&lt;').replace('>', '&gt;')
        else:          title = item.feed.name
        title = self.unescape_utf8_xml(title)
        header.append(title, 'utf-8')
        message['Subject'] = header

        if item.link: message['X-URL'] = item.link

        message['Message-ID'] = item.message_id

        if item.previous_message_id: message['References'] = item.previous_message_id

        message['Date'] =  item.createddate.strftime('%a, %e %b %Y %T -0000')

        message['X-RSS-ID'] = item.id
        message['X-RSS-Categories'] = ', '.join(sorted(item.categories))
        message['X-Keywords'] = ', '.join(sorted(item.keywords))
        message['X-rss2maildir-rundate'] = datetime.datetime.now().strftime('%a, %e %b %Y %T -0000')

        message.set_default_type('text/plain')

        # NOTE: Quoted printable encoder on python 3.3 was affected by this
        # http://bugs.python.org/issue16948
        if html:
            htmlpart = MIMEText(item.html_content, 'html')
            message.attach(htmlpart)
        else:
            textpart = MIMEText(item.text_content, 'plain')
            message.attach(textpart)

        return message



class RssItem(ItemBase):

    def __init__(self, feed, feed_item):
        self.feed = feed

        self.author = feed_item.get('author', None)
        self.title = feed_item.get('title', None)
        self.link = feed_item.get('link', None)
        self.keywords = set(self.feed.keywords)

        # get rid of newlines in the title
        if self.title: self.title = re.sub('\s', ' ', self.title.strip())

        if feed_item.has_key('content'):
            self.content = feed_item['content'][0]['value']
        else:
            self.content = feed_item.get('description', '')

        # \xa0 is 'unbreakable space'
        self.content = self.content.replace('\xa0', ' ')

        self.id = feed_item.get('id', None)

        tags = feed_item.get('tags', [])
        self.categories = set([c['term'].strip() for c in tags if c['term']])

        self.createddate = self.feed.updateddate
        try:
            self.createddate = datetime.datetime(*(feed_item['created_parsed'][0:6]))
        except Exception as e:
            pass

        try:
            self.createddate = datetime.datetime(*(feed_item['published_parsed'][0:6]))
        except Exception as e:
            pass

        try:
            self.createddate = datetime.datetime(*(feed_item['updated_parsed'][0:6]))
        except Exception as e:
            pass

        self.previous_message_id = None
        self.message_id = self._message_id()
        self.compute_hashes()

    @property
    def text_content(self):
        textparser = HTML2Text()
        textparser.feed(self.content)
        return textparser.gettext()

    @property
    def html_content(self):
        return self.content



class WebItem(ItemBase):

    def __init__(self, feed, feed_item):
        self.feed = feed

        self.author = feed.name
        self.title = "Web Update: %s" % feed.name
        self.link = feed.url
        self.keywords = set(self.feed.keywords)

        self.content = feed_item['content']
        self.id = feed_item['id']
        self.categories = set()
        self.createddate = self.feed.updateddate

        self.previous_message_id = None
        self.message_id = self._message_id()
        self.compute_hashes()

    @property
    def text_content(self):
        return self.content

    @property
    def html_content(self):
        return self.content
