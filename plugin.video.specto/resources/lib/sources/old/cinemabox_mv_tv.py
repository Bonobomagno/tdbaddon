# -*- coding: utf-8 -*-

'''
    Specto Add-on
    Copyright (C) 2015 lambda

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
'''


import re,urllib,urlparse,random
import hashlib, string, json
from resources.lib.libraries import cleantitle
from resources.lib.libraries import client
from resources.lib.libraries import control


class source:
    def __init__(self):
        self.base_link = 'http://playboxhd.com'
        self.search_link = '/api/box?type=search&os=Android&v=291.0&k=0&keyword=%s'
        self.sources_link = '/api/box?type=detail&id=%s&os=Android&v=291.0&k=0&al=key'
        self.stream_link = '/api/box?type=stream&id=%s&os=Android&v=291.0'

    def get_movie(self, imdb, title, year):
        mytab = []
        try:
            title = cleantitle.getsearch(title)
            query = self.search_link % (urllib.quote_plus(title))
            query = urlparse.urljoin(self.base_link, query)
            r = client.request(query, mobile=True)
            r = json.loads(r)
            r = r['data']['films']


            r = [i for i in r if cleantitle.get(title) == cleantitle.get(i['title'])]
            years = [str(year),str(int(year)+1),str(int(year)-1)]
            r = [i for i in r if any(x in i['publishDate'] for x in years)][0]
            url = {'imdb': imdb, 'title': title, 'year': year, 'id':r['id']}
            url = urllib.urlencode(url)
            return url


        except:
            return

    def get_show(self, imdb, tvdb, tvshowtitle, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return

    def get_episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:

            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            title = cleantitle.getsearch(title)
            cleanmovie = cleantitle.get(title)
            data['season'], data['episode'] = season, episode
            episodecheck = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
            episodecheck = episodecheck.lower()
            query = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
            ep = "%01d" % (int(data['episode']))
            full_check = 'season%01d' % (int(data['season']))
            full_check = cleanmovie + full_check
            query = self.search_link % (urllib.quote_plus(title), season)
            query = urlparse.urljoin(self.base_link, query)
            r = client.request(query, headers=self.headers)
            # print ("BOBBYAPP", r)
            match = re.compile('alias=(.+?)\'">(.+?)</a>').findall(r)
            for id, name in match:
                name = cleantitle.get(name)
                # print ("BOBBYAPP id name", id, name)
                if full_check == name:
                    type = 'tv_episodes'
                    ep = "%01d" % (int(data['episode']))
                    print ("BOBBYAPP PASSED", id, name)
                    murl = id
            murl = client.replaceHTMLCodes(murl)
            murl = murl.encode('utf-8')

            url = {'imdb': imdb, 'title': title, 'episode': episode, 'url':murl}
            url = urllib.urlencode(url)
            return url
        except Exception as e:
            print "ERROR %s" % e
            return

    def get_sources(self, url, hosthdDict, hostDict, locDict):
        #sources.append({'source': host.split('.')[0], 'quality': 'SD', 'provider': 'Movie25', 'url': url})
        sources = []

        try:
            if url == None: return sources
            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            query = self.sources_link % data['id']
            query = urlparse.urljoin(self.base_link, query)
            r = client.request(query, mobile=True)
            r = json.loads(r)
            if 'episode' in data:
                match = re.compile('changevideo\(\'(.+?)\'\)".+?data-toggle="tab">(.+?)\..+?</a>').findall(r)
                match = [i for i in match if int(i[1]) == int(data['episode']) ]
            else:
                #r = r['data']['chapters'][0]['streams']
                match = re.compile('changevideo\(\'(.+?)\'\)".+?data-toggle="tab">(.+?)</a>').findall(r)

            for i in match:
                print "i", i[0]
                print "i", i[1]

            for href, res in match:
                if 'webapp' in href:
                    href = href.split('embed=')[1]

                if 'google' in href:
                    sources.append({'source': 'gvideo', 'quality': client.googletag(href)[0]['quality'],
                                            'url': href, 'provider': 'Bobby'})
                else:
                    try:
                        host = re.findall('([\w]+[.][\w]+)$', urlparse.urlparse(href.strip().lower()).netloc)[0]
                        if not host in hostDict: raise Exception()
                        host = client.replaceHTMLCodes(host)
                        host = host.encode('utf-8')

                        sources.append({'source': host, 'quality': 'SD', 'url': href, 'provider': 'Bobby'})
                    except:
                        pass
            return sources
        except Exception as e:
            control.log('ERROR Boby %s' % e)
            return sources

    def resolve(self, url):
        return url