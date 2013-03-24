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
import email
import socket
import datetime
from .HTML2Text import HTML2Text
from .utils import generate_random_string, compute_hash

import htmlentitydefs

# Default encoding mode set to Quoted Printable. Acts globally!
email.Charset.add_charset('utf-8', email.Charset.QP, email.Charset.QP, 'utf-8')

class Item(object):
    def __init__(self, feed, feed_item):
        self.feed = feed

        self.author = feed_item.get('author', None)
        self.title = feed_item.get('title', None)
        self.link = feed_item.get('link', None)
        self.keywords = set(self.feed.keywords)

        # get rid of newlines in the title
        if self.title:
            self.title = re.sub('\s', ' ', self.title.strip())

        if feed_item.has_key('content'):
            self.content = feed_item['content'][0]['value']
        else:
            self.content = feed_item.get('description', u'')

        self.md5sum = compute_hash(self.content.encode('utf-8'))
        self.id = feed_item.get('id', None)

        if self.id:      self.md5id = compute_hash(self.id.strip().encode('utf-8'))
        elif self.title: self.md5id = compute_hash(self.title.strip().encode('utf-8'))
        else:            self.md5id = None

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
        self.message_id = '<%s.%s@%s>' % (
            datetime.datetime.now().strftime("%Y%m%d%H%M"),
            generate_random_string(6),
            socket.gethostname()
        )


    def __getitem__(self, key):
        return getattr(self, key)


    def __str__(self):
        ret = u""
        ret = ret + u"Title: %s\n" % self.title
        ret = ret + u"Author: %s\n" % self.author
        ret = ret + u"Keywords: %s\n" % ', '.join(self.keywords)
        ret = ret + u"MD5: %s\n" % self.md5sum
        ret = ret + u"ID: %s\n" % self.id
        ret = ret + u"URL: %s\n" % self.link
        ret = ret + u"Content:\n%s\n" % self.content
        return ret.encode('utf-8')


    def unescape_utf8_xml(self, text):
        def fixup(m):
            txt = m.group(0)
            if txt[:2] == "&#":
                # character reference
                try:
                    if txt[:3] == "&#x":
                        return unichr(int(txt[3:-1], 16))
                    else:
                        return unichr(int(txt[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    txt = unichr(htmlentitydefs.name2codepoint[txt[1:-1]])
                except KeyError:
                    pass
            return txt # leave as is

        return re.sub("&#?[a-zA-Z0-9_]+;", fixup, text, flags=re.UNICODE)



    text_template = u'%(text_content)s\n\nURL: %(link)s'
    html_template = u'%(html_content)s\n<p>URL: <a href="%(link)s">%(link)s</a></p>'
    def create_message(self, html = True):
        item = self
        message = email.MIMEMultipart.MIMEMultipart('alternative')

#       message.set_unixfrom('%s <rss2maildir@localhost>' % item.feed.url)
#       message.add_header('To', '%s <rss2maildir@localhost>' % item.feed.url)

        if item.author:
            message.add_header('From', '%s <rss2maildir@localhost>' % item.author.encode('utf-8'))
        else:
            message.add_header('From', '%s <rss2maildir@localhost>' % item.feed.name.encode('utf-8'))

        message.add_header('To', 'rss2maildir@localhost')

        if item.title: title = item.title.replace(u'<', u'&lt;').replace(u'>', u'&gt;')
        else:          title = item.feed.name
        title = self.unescape_utf8_xml(title).encode('utf-8')
        message.add_header('Subject', title)

        if item.link:
            message.add_header('X-URL', item.link)

        message.add_header('Message-ID', item.message_id)

        if item.previous_message_id:
            message.add_header('References', item.previous_message_id)

        message.add_header('Date', item.createddate.strftime('%a, %e %b %Y %T -0000'))

        message.add_header('X-RSS-ID', item.id)
        message.add_header('X-RSS-Categories', ', '.join(sorted(item.categories)))
        message.add_header('X-Keywords', ', '.join(sorted(item.keywords)))

        message.add_header('X-rss2maildir-rundate',
                       datetime.datetime.now().strftime('%a, %e %b %Y %T -0000'))

        message.set_default_type('text/plain')

        if html:
            htmlpart = email.MIMEText.MIMEText((item.html_template % item).encode('utf-8'), 'html', 'utf-8')
            message.attach(htmlpart)
        else:
            textpart = email.MIMEText.MIMEText((item.text_template % item).encode('utf-8'), 'plain', 'utf-8')
            message.attach(textpart)

        return message


    @property
    def text_content(self):
        textparser = HTML2Text()
        textparser.feed(self.content.encode('utf-8'))
        return textparser.gettext()


    @property
    def html_content(self):
        return self.content
