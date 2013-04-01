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
import html.entities

# Regexps!
re_xml_entity = re.compile(r"&#?[a-zA-Z0-9_]+;", flags=re.UNICODE)

re_arxiv_author_list = re.compile(r'<p>Authors:\s*(.*)\s*</p>')
re_arxiv_author      = re.compile('<a href=".*?"\s*>(.*?)</a>')
re_arxiv_title       = re.compile('^(.*)\s*\(.*\)\s*$')

re_ktheory_author = re.compile('\(([^)]*)\)')
re_ktheory_id = re.compile('http://www.math.uiuc.edu/K-theory/([0-9]*)/')


def _unescape_utf8_xml(text):
    def fixup(m):
        txt = m.group(0)
        if txt[:2] == "&#":
            # character reference
            try:
                if txt[:3] == "&#x": return chr(int(txt[3:-1], 16))
                else:                return chr(int(txt[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                txt = chr(html.entities.name2codepoint[txt[1:-1]])
            except KeyError:
                pass
        return txt # leave as is

    return re_xml_entity.sub(fixup, text)


def _preprint_header(title, authors, link):

    # Remove links from authors and add subject
    subject_str = '<li class="subject"><b>Subject:</b> %s</li>' % title.strip()
    authors_str = '<li class="authors"><b>Authors:</b> %s</li>' % ', '.join(authors)
    pdf_str =    '<li class="pdf"><b>PDF:</b> <a href="%s">%s</a></li>' % (link, link)

    return '<ul class="arxiv_head">\n  %s\n  %s\n  %s\n</ul>\n' % (authors_str, subject_str, pdf_str)



# Filters
# ------------------------------------------------------------------------------

def arxiv(item):
    """Add a header with authors and subject"""
    content = item.content

    # Parse authors from content
    authors = []
    for au in re_arxiv_author.findall(item.author):
        authors.append(_unescape_utf8_xml(au.strip()))

    if len(authors) > 0: item.author = authors[0]
    else:                item.author = ''

    # Clean subject
    m = re_arxiv_title.match(item.title)
    if m: item.title = m.group(1)

    # get pdf link
    pdf_link = re.sub('arxiv.org/abs', 'arxiv.org/pdf', item.link)

    # Add header to the contents
    header = _preprint_header(item.title, authors, pdf_link)
    item.content = header + re_arxiv_author_list.sub('', content)

    # Set feed and message ID to arxiv ID. It seems that arxiv does not provide
    # id's, so feedparser makes their own.
    arxivid = item.link.replace('http://arxiv.org/abs/', '')
    item.message_id = '<%s@arXiv>' % arxivid
    item.id = 'arXiv:%s' % arxivid

    return item


def ktheory(item):
    # Parse authors from content
    authors = []
    for au in re_ktheory_author.findall(item.author):
        authors.append(au.strip())

    if len(authors) > 0: item.author = authors[0]
    else:                item.author = ''

    header = _preprint_header(item.title, authors, item.link)
    item.content = header + item.content

    # Set feed and message ID to k-theory ID
    ktheoryid = re_ktheory_id.sub('\\1', item.link)
    item.message_id = '<%s@ktheory>' % ktheoryid
    item.id = 'ktheory:%s' % ktheoryid

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


def feed_as_author(item):
    """Use feed name as author"""
    item.author = item.feed.name.strip()
    return item


def nonempty(item):
    """Skip items with empty content"""
    if len(item.content.strip()) > 0:
        return item
    else:
        return None
