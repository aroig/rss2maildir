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

        self.guid = feed_item.get('guid', None)
        if self.guid:
            self.db_guid_key = (self.feed.url + u'|' + self.guid).encode('utf-8')
        else:
            self.db_guid_key = None

        self.db_link_key = (self.feed.url + u'|' + feed_item['link']).encode('utf-8')

        self.createddate = datetime.datetime.now()
        if 'updated_parsed' in feed_item:
            updated_parsed = feed_item['updated_parsed'][0:6]
        else:
            updated_parsed = None
        try:
            self.createddate = datetime.datetime(*updated_parsed)
        except TypeError as e:
            pass

        self.previous_message_id = None
        self.message_id = '<%s.%s@%s>' % (
            datetime.datetime.now().strftime("%Y%m%d%H%M"),
            generate_random_string(6),
            socket.gethostname()
        )


    def __getitem__(self, key):
        return getattr(self, key)


    text_template = u'%(text_content)s\n\nItem URL: %(link)s'
    html_template = u'%(html_content)s\n<p>Item URL: <a href="%(link)s">%(link)s</a></p>'
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

        subj_gen = HTML2Text()
        if item.title:
            title = item.title.replace(u'<', u'&lt;').replace(u'>', u'&gt;')
        else:
            title = item.feed.name
        subj_gen.feed(title.encode('utf-8'))
        message.add_header('Subject', subj_gen.gettext().strip())

        if item.link:
            message.add_header('X-URL', item.link)

        message.add_header('Message-ID', item.message_id)

        if item.previous_message_id:
            message.add_header('References', item.previous_message_id)

        message.add_header('Date', item.createddate.strftime('%a, %e %b %Y %T -0000'))

        if len(item.keywords) > 0:
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
