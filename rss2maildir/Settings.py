# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
# Copyright (C) 2011  Justus Winter <4winter@informatik.uni-hamburg.de>
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
import re
from configparser import SafeConfigParser

import importlib.machinery


class FeedConfig(object):

    SECTION_TYPES = ['rss', 'web']

    def __init__(self, cfgdir):
        self.common_section_name = 'common'
        self.general_section_name = 'general'

        cfg_path = os.path.expanduser(os.path.join(cfgdir, 'rss2maildir.conf'))
        self.conf = SafeConfigParser()
        self.conf.read([cfg_path])

        filters_path = os.path.join(cfgdir, 'filters.py')
        self.filters = self._load_filters(filters_path)


    def _load_filters(self, path):

        try:
            loader = importlib.machinery.SourceFileLoader("filters", path)
            module = loader.load_module("filters")
            return module

        except Exception as err:
            raise Exception("Exception loading filters %s\n%s" % (path, str(err)))


    def _guess_section(self, url):
        section = None
        for typ in self.SECTION_TYPES:
            section = '%s %s' % (typ, url)
            if section in self.conf.sections():
                return (typ, section)

        raise KeyError("Can't find section for url %s" % url)


    def has_option(self, url, key, *args, **kwargs):
        typ, section = self._guess_section(url)

        # we handle type as a config key
        if key == 'type': return True

        for location in (section, self.common_section_name):
            if self.conf.has_option(location, key):
                return True

        return False


    def get(self, url, key, *args, **kwargs):
        typ, section = self._guess_section(url)

        # we handle type as a config key
        if key == 'type': return typ

        for location in (section, self.common_section_name):
            if self.conf.has_option(location, key):
                return self.conf.get(location, key, *args, **kwargs)

        raise KeyError('Neither section %s nor %s contained the option %s' %
                       (section, self.common_section_name, key))



    def getlist(self, url, key, *args, **kwargs):
        typ, section = self._guess_section(url)

        value = []
        for location in (self.common_section_name, section):
            if self.conf.has_option(location, key):
                raw = self.conf.get(location, key, *args, **kwargs)
                value = value + [k.strip() for k in raw.split(',') if len(k.strip()) > 0]

        return value


    def getboolean(self, url, key, *args, **kwargs):
        typ, section = self._guess_section(url)

        for location in (section, self.common_section_name):
            if self.conf.has_option(location, key):
                return self.conf.getboolean(location, key, *args, **kwargs)

        raise KeyError('Neither section %s nor %s contained the option %s' %
                       (section, self.common_section_name, key))



    def __contains__(self, key):
        return self.conf.has_option(self.general_section_name, key)


    def __getitem__(self, key):
        return self.conf.get(self.general_section_name, key)


    def __setitem__(self, key, value):
        self.conf.set(self.general_section_name, key, value)


    def feeds(self):
        for section in self.conf.sections():
            for typ in self.SECTION_TYPES:
                m = re.match('%s (.*)' % typ, section)
                if m: yield m.group(1)
