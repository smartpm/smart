# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Per Øyvind Karlsen
#
# Written by Per Øyvind Karlsen <peroyvind@mandriva.org>
#
# This file is part of Smart Package Manager.
#
# Smart Package Manager is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Smart Package Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Smart Package Manager; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import os
from random import random
from math import cos, sqrt, pi

CLOCK = "/etc/sysconfig/clock"
ZONE_TAB = "/usr/share/zoneinfo/zone.tab"

class GeoLocate(object):
    def __init__(self, clock=None, zone_tab=None):
        self._timezone = None
        self._latitude = None
        self._longitude = None
        self._country = None
        self._continent = None

        self._setTimezone(clock or CLOCK, zone_tab or ZONE_TAB)

    def _setTimezone(self, clock, zone_tab):
        coords = None
        zone = None

        fp = open(clock)
        for line in fp.readlines():
            items = line.split("=")
            if items[0].lower() == "zone" and len(items) == 2:
                zone = items[1].strip()
                break
        fp.close()
        if not zone:
            return

        fp = open(zone_tab)
        lines = fp.readlines()
        fp.close()

        tzlist = []
        i = 0
        while i < len(lines):
            fields = lines[i].strip().split()
            i += 1
            if fields[0].startswith("#"):
                continue
            if len(fields) > 2:
                if not coords and fields[0].isupper() and fields[2][0].isupper() and \
                       ((zone.find(fields[2]) != -1) or (fields[2].find(zone) != -1)):
                    self._country = fields[0]
                    coords = fields[1]
                    self._latitude, self._longitude = _deg_min_sec_to_dec(coords)
                    self._timezone = fields[2]
                    i = 0
                elif fields[1] == coords:
                    tzlist.append(fields[2])
        for cont in tzlist:
            continent = cont.split("/")[0]
            if continent == "Europe":
                self._continent = "EU"
            elif continent == "Asia":
                self._continent = "AS"
            elif continent == "America":
                if self._longitude > 12:
                    self._continent = "NA"
                else:
                    self._continent = "SA"
            elif continent == "Africa":
                self._continent = "AF"
            if self._continent:
                break

    def getCoordinates(self):
        return (self._latitude, self._longitude)

    def getTimezone(self):
        return self._timezone

    def getCountry(self):
        return self._country

    def getContinent(self):
        return self._continent
    
    def getProximity(self, latitude, longitude, randomize=True, country=None, continent=None):
        if not (self._latitude and self._longitude):
            return 0
        x = self._latitude - latitude
        y = (self._longitude - longitude) * cos(latitude / 180 * pi)
        proximity = sqrt(x *x + y * y)

        if randomize:
            proximity *= 1 + (random() - 0.5) * 0.05 * 2
        
        if (self._country and country) and (self._country != country):
            proximity *= 0.5
        if (self._continent and continent) and (self._continent != continent):
            if (self._continent == "SA") and (continent == "NA"):
                proximity *= 0.9
            else:
                proximity *= 0.5

        return proximity

def _deg_min_sec_to_dec(coords):
    pos = coords.rfind("-")
    if pos <= 0:
        pos = coords.rfind("+")
    ret = []
    for coord in coords[:pos], coords[pos:]:
        sep = None
        sec = 0
        if len(coord) is (5 or 7):
            sep = 3
        elif len(coord) is (6 or 8):
            sep = 4
        if len(coord) >= 7:
            sec = coord[sep+2:]
        deg = coord[0:sep]
        min = coord[sep:sep+2]
        ret.append(float(deg) + float(min) / 60 + float(sec) / 3600)

    return (ret[0], ret[1])

# vim:ts=4:sw=4:et
