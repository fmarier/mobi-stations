#!/usr/bin/python3
"""
station_list - List all Mobi bike share stations.

Displays the list of all Mobi stations as shown on
https://www.mobibikes.ca/en#the-map.

Copyright (C) 2016, 2017, 2018, 2019, 2022  Francois Marier <francois@fmarier.org>

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
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lxml import html  # nosec

VERSION = '0.1'
MOBI_URL = 'https://www.mobibikes.ca/en/map'

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
    "0021",
    "0024",
    "0025",
    "0026",
    "0027",
    "0028",
    "0030",
    "0031",
    "0032",
    "0033",
    "0034",
    "0035",
    "0036",
    "0037",
    "0039",
    "0040",
    "0041",
    "0044",
    "0045",
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
    "0074",
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
    "0098",
    "0099",
    "0101",
    "0102",
    "0103",
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
    "0124",
    "0125",
    "0126",
    "0129",
    "0130",
    "0132",
    "0133",
    "0134",
    "0136",
    "0137",
    "0138",
    "0139",
    "0140",
    "0142",
    "0143",
    "0147",
    "0148",
    "0150",
    "0152",
    "0153",
    "0154",
    "0155",
    "0159",
    "0161",
    "0166",
    "0167",
    "0170",
    "0171",
    "0172",
    "0173",
    "0174",
    "0176",
    "0177",
    "0179",
    "0180",
    "0186",
    "0187",
    "0189",
    "0190",
    "0191",
    "0192",
    "0193",
    "0197",
    "0198",
    "0199",
    "0201",
    "0202",
    "0203",
    "0204",
    "0205",
    "0206",
    "0207",
    "0208",
    "0209",
    "0211",
    "0212",
    "0213",
    "0215",
    "0217",
    "0218",
    "0219",
    "0221",
    "0222",
    "0223",
    "0224",
    "0225",
    "0227",
    "0228",
    "0229",
    "0230",
    "0231",
    "0232",
    "0233",
    "0234",
    "0235",
    "0236",
    "0237",
    "0239",
    "0240",
    "0241",
    "0242",
    "0244",
    "0245",
    "0246",
    "0248",
    "0249",
    "0250",
    "0252",
    "0253",
    "0254",
    "0255",
    "0256",
    "0257",
    "0258",
    "0260",
    "0261",
    "0262",
    "0265",
    "0266",
    "0272",
    "0273",
    "0274",
    "0278",
    "0280",
    "0281",
    "0282",
    "0283",
    "0285",
    "0287",
    "0297",
    "0298",
    "0300",
    "0305",
]
KNOWN_DISUSED_STATIONS = [
]

# pylint: disable=invalid-name
stations = {}
new_stations = []
all_stations = []


def osm_link(latitude, longitude):
    """Return OSM link for a given lattidue and longitude."""
    zoom_level = 17
    return "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=%s/%s/%s" % (latitude, longitude, zoom_level, latitude, longitude)


def print_station(ref, data):
    """Output all station metadata."""
    print("%s:" % ref)
    print("  name=%s" % data["name"])
    print("  capacity=%s" % data["capacity"])
    if data["disused"]:
        print("  disused=yes")
    print("  latitude=%s" % data["latitude"])
    print("  longitude=%s" % data["longitude"])
    print("  %s" % osm_link(data["latitude"], data["longitude"]))


def print_stations(verbose, quiet):
    """Output all stations with their metadata along with deleted stations."""
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
    """Output a summary of the number of known and advertised stations."""
    need_newline = False
    if not quiet:
        print("Known stations: %s" % len(KNOWN_STATIONS))
        print("Known disused stations: %s" % len(KNOWN_DISUSED_STATIONS))
        print("Stations advertised: %s" % len(stations))
        need_newline = True
    if new_stations:
        print("New stations: %s" % len(new_stations))
        need_newline = True
    if need_newline:
        print("")


def process_markers(markers):
    """Parse the markers extracted from the config of the Mobi homepage."""
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

            if ref in ("0000", "0997", "1000"):  # leave temporary stations out
                continue

            all_stations.append(ref)
            if not disused and ref not in KNOWN_STATIONS:
                new_stations.append(ref)
            elif disused and ref not in KNOWN_DISUSED_STATIONS:
                new_stations.append(ref)


def process_script(script):
    """Extract metadata out of the Drupal settings variable."""
    text = script.replace('jQuery.extend(Drupal.settings, ', '')
    text = text.replace('});', '}')
    data = json.loads(text)
    process_markers(data['markers'])


def process_html(page):
    """Extract the Drupal config out of the Mobi homepage."""
    tree = html.fromstring(page)
    scripts = tree.xpath('//script/text()')
    for script in scripts:
        if 'Drupal.settings' in script:
            process_script(script)


def download_html(url):
    """Download the HTML from the Mobi homepage in an efficient way."""
    # Disable all certificate checking because the Mobi TLS config is garbage.
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    request = Request(url, headers={'Accept-encoding': 'gzip'})
    response = urlopen(request, context=context)  # nosec

    if response.info().get('Content-Encoding') == 'gzip':
        buf = io.BytesIO(response.read())
        response = gzip.GzipFile(fileobj=buf)

    return response.read()


def main():
    """Parse arguments and start the whole process."""
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
    except URLError as e:
        print("Error while downloading the map: %s" % e, file=sys.stderr)
        return False

    print_stats(args.quiet)
    print_stations(args.verbose, args.quiet)
    return True


if main():
    sys.exit(0)
else:
    sys.exit(1)
