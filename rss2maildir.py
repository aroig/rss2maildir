#!/usr/bin/env python
# coding=utf-8

# rss2maildir.py - RSS feeds to Maildir 1 email per item
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
import logging
from optparse import OptionParser

from rss2maildir.rss2maildir import main
__version__ = "0.1"



# Main stuff
#------------------------

usage = """Usage: %prog [options]
  """
parser = OptionParser(usage=usage)

# Main commands

parser.add_option("-c", "--conf", action="store", type="string",  default=None, dest="conf",
                  help="Config path.")

parser.add_option("--version", action="store_true", default=False, dest="version",
                  help="Print the version and exit")

parser.add_option("--debug", action="store_true", default=False, dest="debug",
                  help="Print debug information")

parser.add_option('-v', '--verbose', dest = 'verbosity', action = 'count', default = 0,
                   help = 'be more verbose, can be given multiple times')


(opts, args) = parser.parse_args()

if opts.version:
    print(__version__)
    sys.exit(0)

try:
    main(opts, args)

except KeyboardInterrupt:
    print("")
    sys.exit()

except EOFError:
    print("")
    sys.exit()
