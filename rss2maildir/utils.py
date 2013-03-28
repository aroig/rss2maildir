# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
#
# Copyright (C) 2007  Brett Parker <iDunno@sommitrealweird.co.uk>
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

import sys
import os
import errno
import random
import string
import logging

import hashlib as md5


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def make_maildir(path):
    for dirname in (os.path.join(path, subdir)
                    for subdir in ('cur', 'tmp', 'new')):
        mkdir_p(dirname)


def generate_random_string(length,
                           character_set = string.ascii_letters + string.digits):
    return ''.join(random.choice(character_set) for n in range(length))


def compute_hash(data):
    return md5.md5(data.encode('utf-8')).hexdigest()
