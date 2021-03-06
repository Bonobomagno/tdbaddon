"""
    SALTS XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
import urlparse
import kodi
import log_utils  # @UnusedImport
import dom_parser2
from salts_lib import scraper_utils
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import VIDEO_TYPES
import scraper


BASE_URL = 'http://www.dizigold1.com'
AJAX_URL = '/sistem/ajax.php'
XHR = {'X-Requested-With': 'XMLHttpRequest'}

class Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))
        self.ajax_url = urlparse.urljoin(self.base_url, AJAX_URL)

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.EPISODE])

    @classmethod
    def get_name(cls):
        return 'Dizigold'

    def get_sources(self, video):
        hosters = []
        sources = []
        source_url = self.get_url(video)
        if not source_url or source_url == FORCE_NO_MATCH: return hosters
        page_url = urlparse.urljoin(self.base_url, source_url)
        html = self._http_get(page_url, cache_limit=.25)
        match = re.search('var\s+view_id\s*=\s*"([^"]+)', html)
        if not match: return hosters
        
        view_data = {'id': match.group(1), 'tip': 'view', 'dil': 'or'}
        html = self._http_get(self.ajax_url, data=view_data, headers=XHR, cache_limit=.25)
        html = html.strip()
        html = re.sub(r'\\n|\\t', '', html)
        match = re.search('var\s+sources\s*=\s*(\[.*?\])', html)
        if match:
            raw_data = match.group(1)
            raw_data = raw_data.replace('\\', '')
        else:
            raw_data = html
        
        js_data = scraper_utils.parse_json(raw_data, self.ajax_url)
        if 'data' in js_data:
            src = dom_parser2.parse_dom(js_data['data'], 'iframe', req='src')
            if src:
                html = self._http_get(src[0].attrs['src'], cache_limit=.25)
                for attrs, _content in dom_parser2.parse_dom(html, 'iframe', req='src'):
                    src = attrs['src']
                    if not src.startswith('http'): continue
                    sources.append({'label': '720p', 'file': src, 'direct': False})

                for match in re.finditer('"file"\s*:\s*"([^"]+)"\s*,\s*"label"\s*:\s*"([^"]+)', html):
                    sources.append({'label': match.group(2), 'file': match.group(1), 'direct': True})
        else:
            sources = js_data

        for source in sources:
            direct = source.get('direct', True)
            stream_url = source['file'] + scraper_utils.append_headers({'User-Agent': scraper_utils.get_ua()})
            if direct:
                host = scraper_utils.get_direct_hostname(self, stream_url)
                if host == 'gvideo':
                    quality = scraper_utils.gv_get_quality(stream_url)
                else:
                    quality = scraper_utils.height_get_quality(source['label'])
            else:
                host = urlparse.urlparse(stream_url).hostname
                quality = scraper_utils.height_get_quality(source['label'])
        
            hoster = {'multi-part': False, 'host': host, 'class': self, 'quality': quality, 'views': None, 'rating': None, 'url': stream_url, 'direct': direct}
            hosters.append(hoster)
    
        return hosters

    def _get_episode_url(self, show_url, video):
        episode_pattern = 'href="([^"]+/%s-sezon/%s-[^"]*bolum[^"]*)' % (video.season, video.episode)
        title_pattern = 'href="(?P<url>[^"]+)"\s+class="realcuf".*?<p\s+class="realcuf">(?P<title>[^<]+)'
        return self._default_get_episode_url(show_url, video, episode_pattern, title_pattern)

    def search(self, video_type, title, year, season=''):  # @UnusedVariable
        results = []
        html = self._http_get(self.base_url, cache_limit=48)
        fragment = dom_parser2.parse_dom(html, 'div', {'class': 'dizis'})
        if not fragment: return results
        
        norm_title = scraper_utils.normalize_title(title)
        for attrs, match_title in dom_parser2.parse_dom(fragment[0].content, 'a', req='href'):
            match_url = attrs['href']
            match_title = re.sub('<div[^>]*>.*?</div>', '', match_title)
            if norm_title in scraper_utils.normalize_title(match_title):
                result = {'url': scraper_utils.pathify_url(match_url), 'title': scraper_utils.cleanse_title(match_title), 'year': ''}
                results.append(result)

        return results
