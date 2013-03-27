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

def arxiv(item):
    """Add a header with authors and subject"""
    re_author_list = re.compile(r'<p>Authors:\s*(.*)\s*</p>')
    re_author      = re.compile('<a href=".*?"\s*>(.*?)</a>')
    re_title       = re.compile('^(.*)\s*\(.*\)\s*$')

    content = item.content

    # Parse authors from content
    authors = []
    m = re_author_list.match(content)
    if m:
        for au in re_author.findall(m.group(1)):
            authors.append(au.strip())

    # Clean subject
    m = re_title.match(item.title)
    if m: item.title = m.group(1)

    # get pdf link
    pdf_link = re.sub('arxiv.org/abs', 'arxiv.org/pdf', item.link)

    # Remove links from authors and add subject
    subject_str = '<li class="subject"><b>Subject:</b> %s</li>' % item.title.strip()
    authors_str = '<li class="authors"><b>Authors:</b> %s</li>' % ', '.join(authors)
    pdf_str =    '<li class="pdf"><b>PDF:</b> <a href="%s">%s</a></li>' % (pdf_link, pdf_link)
    item.content = '<ul class="arxiv_head">\n  %s\n  %s\n  %s\n</ul>\n' % (authors_str, subject_str, pdf_str) + \
                   re_author_list.sub(u'', content)

    # Set message ID to arxiv ID
    if item.id: item.message_id = '<%s@arXiv>' % item.id

    return item


def blogger(item):
    """Clean up 'from' string"""
    item.author = re.sub('\([^()]*\)', '', item.author).strip()
    return item


def addurl(item):
    """Add an html-formated URL at the end of content"""
    content_str = item.content
    url_str = '<p>URL: <a href="%s">%s</a></p>' % (item.link, item.link)
    item.content = '%s\n\n%s' % (content_str, url_str)
    return item
