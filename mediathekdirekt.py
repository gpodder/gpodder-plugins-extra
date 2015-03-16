#
# gPodder: Media and podcast aggregator
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# MediathekDirect plugin for gPodder
# Thomas Perl <thp@gpodder.org>; 2014-10-29

import gpodder

from gpodder import registry
from gpodder import util
from gpodder import directory

import os
import re
import datetime





class MediathekDirektFeed(object):
    KEYS = [
        'station',
        'show',
        'episode',
        'date',
        'duration',
        'description',
        'enclosure',
        'link',
        '_unknown',
    ]

    def __init__(self, station=None, show=None):
        self.station = station
        self.show = show
        self.json_sources = [
            'http://www.mediathekdirekt.de/good.json',
        ]

    def was_updated(self):
        return True

    def get_etag(self, default):
        return default

    def get_modified(self, default):
        return default

    def get_title(self):
        if self.station is None:
            return 'Mediathekdirekt.de'
        elif self.show is None:
            return '{} (MediathekDirekt.de)'.format(self.station)
        else:
            return '{} auf {} (MediathekDirekt.de)'.format(self.show, self.station)

    def get_image(self):
        return 'http://www.mediathekdirekt.de/images/mediathekdirekt.png'

    def get_link(self):
        return 'http://www.mediathekdirekt.de/'

    def get_description(self):
        return 'MediathekDirekt ist eine Art "Suchmaschine" für die Inhalte der öffentlich-rechtlichen Fernsehmediatheken und ein einfaches Frontend für die mit MediathekView erstellte Filmliste.'

    def get_payment_url(self):
        return None

    def _to_episode(self, track):
        if track['time']:
            dt = datetime.datetime.strptime(' '.join((track['date'], track['time'])), '%d.%m.%Y %H:%M:%S')
        else:
            dt = datetime.datetime.strptime(track['date'], '%d.%m.%Y')

        return {
            'title': '{} - {}'.format(track['station'], track['show']),
            'subtitle': track['episode'],
            'description': track['description'],
            'published': int(dt.strftime('%s')),
            #'duration': parse_duration(track['duration']),
            'url': track['enclosure'],
            'link': track['link'],
        }

    def _get_tracks(self):
        for url in self.json_sources:
            for track in util.read_json(url):
                yield dict(list(zip(self.KEYS, track)))

    def get_new_episodes(self, channel):
        tracks = list(self._get_tracks())
        existing_guids = [episode.guid for episode in channel.episodes]
        seen_guids = []
        new_episodes = []

        for track in tracks:
            if self.station is not None and track['station'] != self.station:
                continue

            if self.show is not None and track['show'] != self.show:
                continue

            seen_guids.append(track['enclosure'])

            if track['enclosure'] not in existing_guids:
                episode = channel.episode_factory(self._to_episode(track).items())
                episode.save()
                new_episodes.append(episode)

        return new_episodes, seen_guids


@registry.feed_handler.register
def mediathekdirekt_feed_handler(channel, max_episodes):
    m = re.match(r'http://www.mediathekdirekt.de/\?([^/]+)/(.*)', channel.url)
    if channel.url == 'http://www.mediathekdirekt.de/':
        return MediathekDirektFeed()
    elif m:
        return MediathekDirektFeed(m.group(1), m.group(2))


@registry.directory.register_instance
class MediathekDirektProvider(directory.Provider):
    def __init__(self):
        self.name = 'Mediathek Direkt'
        self.kind = directory.Provider.PROVIDER_SEARCH
        self.priority = 0

    def on_search(self, query):
        query = query.lower()

        f = MediathekDirektFeed()
        station_show_set = set()
        for track in f._get_tracks():
            if query in track['station'].lower() or query in track['show'].lower() or query in track['episode'].lower():
                station_show_set.add((track['station'], track['show']))

        for station, show in sorted(station_show_set):
            yield directory.DirectoryEntry('{} auf {}'.format(show, station),
                    'http://www.mediathekdirekt.de/?{}/{}'.format(show, station))
