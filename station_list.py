#!/usr/bin/python3
"""
station_list - List all Mobi bike share stations.

Displays the list of all Mobi stations as shown on
https://www.mobibikes.ca/en#the-map.

Copyright (C) 2016, 2017  Francois Marier <francois@fmarier.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import gzip
import io
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lxml import html

VERSION = '0.1'
MOBI_URL = 'https://www.mobibikes.ca/en#the-map'

KNOWN_STATIONS = [
    "0001",
    "0002",
    "0004",
    "0005",
    "0006",
    "0007",
    "0008",
    "0009",
    "0010",
    "0011",
    "0012",
    "0014",
    "0015",
    "0016",
    "0017",
    "0019",
    "0024",
    "0025",
    "0026",
    "0027",
    "0028",
    "0030",
    "0031",
    "0032",
    "0033",
    "0035",
    "0036",
    "0037",
    "0039",
    "0040",
    "0041",
    "0044",
    "0047",
    "0048",
    "0050",
    "0052",
    "0053",
    "0054",
    "0055",
    "0057",
    "0058",
    "0060",
    "0063",
    "0064",
    "0065",
    "0066",
    "0068",
    "0069",
    "0070",
    "0071",
    "0072",
    "0073",
    "0076",
    "0077",
    "0078",
    "0079",
    "0080",
    "0081",
    "0082",
    "0083",
    "0084",
    "0087",
    "0088",
    "0089",
    "0092",
    "0093",
    "0096",
    "0101",
    "0102",
    "0104",
    "0105",
    "0106",
    "0107",
    "0108",
    "0109",
    "0110",
    "0112",
    "0113",
    "0114",
    "0115",
    "0119",
    "0123",
    "0125",
    "0129",
    "0130",
    "0132",
    "0133",
    "0134",
    "0137",
    "0138",
    "0140",
    "0147",
    "0148",
    "0150",
    "0151",
    "0152",
    "0153",
    "0154",
    "0155",
    "0159",
    "0165",
    "0166",
    "0167",
    "0171",
    "0172",
    "0173",
    "0174",
    "0176",
    "0187",
    "0196",
    "0197",
    "0198",
    "0201",
    "0203",
    "0204",
    "0205",
    "0206",
    "0208",
    "0209",
    "0211",
    "0212",
    "0218",
]
KNOWN_DISUSED_STATIONS = [
]

# pylint: disable=invalid-name
stations = {}
new_stations = []
all_stations = []


def osm_link(latitude, longitude):
    zoom_level = 17
    return "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=%s/%s/%s" % (latitude, longitude, zoom_level, latitude, longitude)


def print_station(ref, data):
    print("%s:" % ref)
    print("  name=%s" % data["name"])
    print("  capacity=%s" % data["capacity"])
    if data["disused"]:
        print("  disused=yes")
    print("  latitude=%s" % data["latitude"])
    print("  longitude=%s" % data["longitude"])
    print("  %s" % osm_link(data["latitude"], data["longitude"]))


def print_stations(verbose, quiet):
    need_newline = False
    for ref in sorted(stations):
        data = stations[ref]
        if verbose or ref in new_stations:
            print_station(ref, data)
            need_newline = True

    if len(KNOWN_STATIONS) != len(all_stations):
        if need_newline:
            print()
            need_newline = False

        for ref in sorted(KNOWN_STATIONS):
            if ref not in all_stations:
                print("%s is no longer advertised" % ref)
                need_newline = True

    if not quiet:
        if need_newline:
            print()
        print(sorted(all_stations))


def print_stats(quiet):
    need_newline = False
    if not quiet:
        print("Known stations: %s" % len(KNOWN_STATIONS))
        print("Known disused stations: %s" % len(KNOWN_DISUSED_STATIONS))
        print("Stations advertised: %s" % len(stations))
        need_newline = True
    if len(new_stations):
        print("New stations: %s" % len(new_stations))
        need_newline = True
    if need_newline:
        print("")


def process_markers(markers):
    for marker in markers:
        if not marker["poi"]:
            # Temporary station
            ref = '0000'
            name = marker["title"]
            if marker["title"][0] != '-' and marker["title"][4] == ' ':
                # Permanent station
                ref = marker["title"][0:4]
                name = marker["title"][5:]

            capacity = marker["total_slots"]
            latitude = marker["latitude"]
            longitude = marker["longitude"]
            disused = marker["operative"] != '1'
            stations[ref] = {
                "name": name,
                "capacity": capacity,
                "disused": disused,
                "latitude": latitude,
                "longitude": longitude
            }
            if not disused and ref not in KNOWN_STATIONS:
                new_stations.append(ref)
            elif disused and ref not in KNOWN_DISUSED_STATIONS:
                new_stations.append(ref)
            if ref != "0000":  # leave temporary stations out
                all_stations.append(ref)


def process_script(script):
    text = script.replace('jQuery.extend(Drupal.settings, ', '')
    text = text.replace('});', '}')
    data = json.loads(text)
    process_markers(data['markers'])


def process_html(page):
    tree = html.fromstring(page)
    scripts = tree.xpath('//script/text()')
    for script in scripts:
        if 'Drupal.settings' in script:
            process_script(script)


def download_html(url):
    request = Request(url, headers={'Accept-encoding': 'gzip'})
    response = urlopen(request)

    if response.info().get('Content-Encoding') == 'gzip':
        buf = io.BytesIO(response.read())
        response = gzip.GzipFile(fileobj=buf)

    return response.read()


def main():
    parser = argparse.ArgumentParser(
        description='Display the list of all Mobi stations as shown on %s.' % MOBI_URL)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='display all station details')
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                        help='suppres output unless there are new stations')
    parser.add_argument('-V', '--version', action='version',
                        version='station_list %s' % VERSION)
    args = parser.parse_args()
    if args.verbose and args.quiet:
        print("Error: --quiet and --verbose are mutually exclusive", file=sys.stderr)
        return False

    try:
        process_html(download_html(MOBI_URL))
    except HTTPError as e:
        print("Error while downloading the map: %s" % e, file=sys.stderr)
        return False

    print_stats(args.quiet)
    print_stations(args.verbose, args.quiet)


if main():
    exit(0)
else:
    exit(1)
