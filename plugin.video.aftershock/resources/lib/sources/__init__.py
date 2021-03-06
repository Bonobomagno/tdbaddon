# -*- coding: utf-8 -*-

'''
    Aftershock Add-on
    Copyright (C) 2017 Aftershockpy

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

import datetime
import json
import os
import pkgutil
import random
import re
import sys
import time
import urllib
import urlparse

try: import xbmc
except: pass

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from ashock.modules import control
from ashock.modules import cleantitle
from ashock.modules import client
from ashock.modules import workers
from ashock.modules import debrid
from ashock.modules import cache
from resources.lib import resolvers
from ashock.modules import logger

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])

class sources:
    def __init__(self):
        self.resolverList = self.getResolverList()
        self.hostDict = self.getHostDict()
        self.hostprDict = self.getHostPrDict()
        self.srcs = []
        self.debridDict = debrid.debridDict()
        self.itemProperty = "%s.itemProperty" % control.addonInfo('name')
        self.metaProperty = "%s.itemMeta" % control.addonInfo('name')

    def addItem(self, title, content):
        try:
            control.playlist.clear()

            items = control.window.getProperty(self.itemProperty)
            items = json.loads(items)

            if items == []: raise Exception()

            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            infoMenu = control.lang(30502).encode('utf-8')

            downloads = True if control.setting('downloads') == 'true' and not control.setting('movie.download.path') == '' else False

            if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
                name = '%s S%02dE%02d' % (title, int(meta['season']), int(meta['episode']))
            elif 'year' in meta:
                name = '%s (%s)' % (title, meta['year'])
            else:
                name = title

            systitle = urllib.quote_plus(title.encode('utf-8'))

            sysname = urllib.quote_plus(name.encode('utf-8'))

            poster = meta['poster'] if 'poster' in meta else '0'
            banner = meta['banner'] if 'banner' in meta else '0'
            thumb = meta['thumb'] if 'thumb' in meta else poster
            fanart = meta['fanart'] if 'fanart' in meta else '0'

            if poster == '0': poster = control.addonPoster()
            if banner == '0' and poster == '0': banner = control.addonBanner()
            elif banner == '0': banner = poster
            if thumb == '0' and fanart == '0': thumb = control.addonFanart()
            elif thumb == '0': thumb = fanart
            if control.setting('fanart') == 'true' and not fanart == '0': pass
            else: fanart = control.addonFanart()

            for i in range(len(items)):
                try :
                    parts = int(items[i]['parts'])
                except:
                    parts = 1

                label = items[i]['label']

                syssource = urllib.quote_plus(json.dumps([items[i]]))

                sysurl = '%s?action=playItem&title=%s&source=%s&content=%s' % (sysaddon, systitle, syssource, content)

                item = control.item(label=label)

                cm = []
                cm.append((control.lang(30504).encode('utf-8'), 'RunPlugin(%s?action=queueItem)' % sysaddon))
                if content != 'live':
                    if downloads == True and parts <= 1:
                        sysimage = urllib.quote_plus(poster.encode('utf-8'))
                        cm.append((control.lang(30505).encode('utf-8'), 'RunPlugin(%s?action=download&name=%s&image=%s&source=%s)' % (sysaddon, systitle, sysimage, syssource)))
                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': poster, 'tvshow.poster': poster, 'season.poster': poster, 'banner': banner, 'tvshow.banner': banner, 'season.banner': banner})

                if not fanart == None: item.setProperty('Fanart_Image', fanart)

                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels = meta)

                control.addItem(handle=syshandle, url=sysurl, listitem=item, isFolder=False)

            control.directory(syshandle, cacheToDisc=True)
        except Exception as e:
            logger.error(e.message)
            control.infoDialog(control.lang(30501).encode('utf-8'))

    def play(self, name, title, year, imdb, tvdb, season, episode, tvshowtitle, date, meta, url, select=None):
        try:
            if not control.infoLabel('Container.FolderPath').startswith('plugin://'):
                control.playlist.clear()

            control.resolve(syshandle, True, control.item(path=''))
            control.execute('Dialog.Close(okdialog)')

            if imdb == '0': imdb = '0000000'
            imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

            if title == None and tvshowtitle == None :
                content = 'live'
            else :
                content = 'movie' if tvshowtitle == None else 'episode'

            self.srcs = self.getSources(name, title, year, imdb, tvdb, season, episode, tvshowtitle, date, meta)

            items = self.sourcesFilter()

            if len(items) > 0:


                try :
                    if content == 'live':
                        if select == None:
                            select = control.setting('live_host_select')
                        select = '2' if len(items) == 1 else select
                        title = name
                        meta = self.srcs[0]['meta']

                        logger.debug('Content is live hence setting %s' % select, __name__)
                    else:
                        select = control.setting('host_select') if select == None else select
                except:
                    pass

                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(items))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, meta)

                    control.sleep(200)

                    return control.execute('Container.Update(%s?action=addItem&title=%s&content=%s)' % (sysaddon, urllib.quote_plus(title.encode('utf-8')), content))

                elif select == '0' or select == '1':
                    url = self.sourcesDialog(items)

                else:
                    url = self.sourcesDirect(items)

            if url == None: raise Exception()
            if url == 'close://': return

            if control.setting('playback_info') == 'true':
                control.infoDialog(self.selectedSource, heading=name)

            control.sleep(200)

            from ashock.modules.player import player
            player().run(content, name, url, year, imdb, tvdb, meta)

            return url
        except Exception as e:
            logger.error(e.message)
            control.infoDialog(control.lang(30501).encode('utf-8'))

    def playItem(self, content, title, source):
        try:
            control.resolve(syshandle, True, control.item(path=''))
            control.execute('Dialog.Close(okdialog)')

            next = [] ; prev = [] ; total = []
            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            year = meta['year'] if 'year' in meta else None
            imdb = meta['imdb'] if 'imdb' in meta else None
            tvdb = meta['tvdb'] if 'tvdb' in meta else None


            for i in range(1,10000):
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))

                    if u in total: raise Exception()
                    total.append(u)
                    u = dict(urlparse.parse_qsl(u.replace('?','')))
                    if 'meta' in u: meta = u['meta']
                    u = json.loads(u['source'])[0]
                    next.append(u)
                except:
                    break
            for i in range(-10000,0)[::-1]:
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total: raise Exception()
                    total.append(u)
                    u = dict(urlparse.parse_qsl(u.replace('?','')))
                    if 'meta' in u: meta = u['meta']
                    u = json.loads(u['source'])[0]
                    prev.append(u)
                except:
                    break

            items = json.loads(source)
            items = [i for i in items+next+prev][:40]

            self.progressDialog = control.progressDialog
            self.progressDialog.create(control.addonInfo('name'), '')
            self.progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    self.progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))

                    if items[i]['source'] == block: raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    m = ''

                    for x in range(3600):
                        if self.progressDialog.iscanceled(): return self.progressDialog.close()
                        if xbmc.abortRequested == True: return sys.exit()
                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        time.sleep(1.0)

                    for x in range(3600):
                        if m == '': break
                        if self.progressDialog.iscanceled(): return self.progressDialog.close()
                        if xbmc.abortRequested == True: return sys.exit()
                        if w.is_alive() == False: break
                        time.sleep(1.0)


                    if w.is_alive() == True: block = items[i]['source']

                    if self.url == None: raise Exception()


                    try: self.progressDialog.close()
                    except: pass

                    control.sleep(200)

                    if control.setting('playback_info') == 'true':
                        control.infoDialog(items[i]['label'])

                    from ashock.modules.player import player
                    player().run(content, title, self.url, year, imdb, tvdb, meta)

                    return self.url
                except:
                    pass

            try: self.progressDialog.close()
            except: pass

            raise Exception()

        except Exception as e:
            logger.error(e.message)
            control.infoDialog(control.lang(30501).encode('utf-8'))
            pass

    def getSources(self, name, title, year, imdb, tvdb, season, episode, tvshowtitle, date, meta=None):
        sourceDict = []
        channelName = name

        for package, name, is_pkg in pkgutil.walk_packages(__path__): sourceDict.append((name, is_pkg))
        sourceDict = [i[0] for i in sourceDict if i[1] == False]
        sourceDict = [(i, __import__(i, globals(), locals(), [], -1).source()) for i in sourceDict]

        if tvshowtitle == None and title == None:
            content = 'live'
            genre = None
            try :genre = meta['genre']
            except:pass
        else:
            content = 'movie' if tvshowtitle == None else 'episode'

        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
        elif content == 'episode':
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
        elif content == 'live':
            sourceDict = [(i[0], i[1], getattr(i[1], 'livetv', None)) for i in sourceDict]

        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == None]

        try: sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except: sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == 'false']

        threads = []

        control.makeFile(control.dataPath)
        self.sourceFile = control.sourcescacheFile

        #sourceDict = [i[0] for i in sourceDict if i[1] == 'true']

        logger.debug('Content [%s] Source Dict : %s' % (content, sourceDict), __name__)

        if content == 'movie':
            title = cleantitle.normalize(title)
            for source in sourceDict: threads.append(
                workers.Thread(self.getMovieSource, title, year, imdb, source[0], source[1]))
        elif content == 'episode':
            tvshowtitle = cleantitle.normalize(tvshowtitle)
            for source in sourceDict: threads.append(
                workers.Thread(self.getEpisodeSource, title, year, imdb, tvdb, season, episode, tvshowtitle, date, source[0], source[1], meta))
        elif content == 'live':
            for source in sourceDict:threads.append(
                workers.Thread(self.getLiveSource, channelName, genre, source[0], source[1]))

        sourceLabel = [(i[0].upper()) for i in sourceDict]

        try: timeout = int(control.setting('sources_timeout_40'))
        except: timeout = 40

        [i.start() for i in threads]

        control.idle()

        self.progressDialog = control.progressDialog
        self.progressDialog.create(control.addonInfo('name'), '')
        self.progressDialog.update(0)

        string1 = control.lang(30512).encode('utf-8')
        string2 = control.lang(30513).encode('utf-8')
        string3 = control.lang(30514).encode('utf-8')

        for i in range(0, timeout * 2):
            try:
                if xbmc.abortRequested == True: return sys.exit()

                try: info = [sourceLabel[int(re.sub('[^0-9]', '', str(x.getName()))) - 1] for x in threads if x.is_alive() == True]
                except: info = []

                if len(info) > 5: info = len(info)

                self.progressDialog.update(int((100 / float(len(threads))) * len([x for x in threads if x.is_alive() == False])), str('%s: %s %s' % (string1, int(i * 0.5), string2)), str('%s: %s' % (string3, str(info).translate(None, "[]'"))))

                if self.progressDialog.iscanceled(): break

                is_alive = [x.is_alive() for x in threads]
                if all(x == False for x in is_alive): break
                time.sleep(0.5)
            except:
                pass

        self.progressDialog.close()

        for i in range(0, len(self.srcs)): self.srcs[i].update({'content': content})

        return self.srcs

    def getMovieSource(self, title, year, imdb, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
        except:
            pass

        try:
            srcs = []
            dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update == False:
                srcs = json.loads(match[4])
                return self.srcs.extend(srcs)
        except:
            pass

        try:
            url = None
            dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = url[4]
        except:
            pass

        try:
            if url == None: url = call.movie(imdb, title, year)
            if url == None: raise Exception()
            dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', url))
            dbcon.commit()
        except:
            pass

        try:
            srcs = []
            logger.debug('[%s] Call %s type(call) : %s' % (source, call, type(call)), __name__)
            srcs = call.sources(url)
            if srcs == None:
                raise Exception()

            self.srcs.extend(srcs)
            dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '', '', json.dumps(srcs), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception as e:
            logger.error(e)
            pass

    def getEpisodeSource(self, title, year, imdb, tvdb, season, episode, tvshowtitle, date, source, call, meta=None):
        meta = json.loads(meta)

        try :
            if season == '0' or episode == '0':
                imdb = meta['tvshowtitle']
                episode = meta['title']
            try:
                dbcon = database.connect(self.sourceFile)
                dbcur = dbcon.cursor()
                dbcur.execute("CREATE TABLE IF NOT EXISTS rel_url (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""rel_url TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
                dbcur.execute("CREATE TABLE IF NOT EXISTS rel_src (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, ""UNIQUE(source, imdb_id, season, episode)"");")
            except:
                pass

            try:
                srcs = []
                dbcur.execute("SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
                match = dbcur.fetchone()
                t1 = int(re.sub('[^0-9]', '', str(match[5])))
                t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
                update = abs(t2 - t1) > 60
                if update == False:
                    srcs = json.loads(match[4])
                    return self.srcs.extend(srcs)
            except:
                pass

            try:
                url = None
                dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                url = dbcur.fetchone()
                url = url[4]
            except:
                pass

            try:
                if url == None:
                    tvshowurl = meta['tvshowurl']
                    url = call.tvshow(tvshowurl, imdb, tvdb, tvshowtitle, year)
                if url == None: raise Exception()
                dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, '', ''))
                dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', url))
                dbcon.commit()
            except:
                pass

            try:
                ep_url = None
                dbcur.execute("SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
                ep_url = dbcur.fetchone()
                ep_url = ep_url[4]
            except:
                pass


            try:
                if url == None: raise Exception()
                if ep_url == None:
                    ep_url = call.episode(url, meta['url'], imdb, tvdb, title, date, season, episode)
                if ep_url == None: raise Exception()
                dbcur.execute("DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
                dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, ep_url))
                dbcon.commit()
            except:
                pass

            try:
                srcs = []
                srcs = call.sources(ep_url)
                if srcs == None: srcs = []
                self.srcs.extend(srcs)
                dbcur.execute("DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" % (source, imdb, season, episode))
                dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season, episode, json.dumps(srcs), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                dbcon.commit()
            except:
                pass
        except:
            client.printException('sources.getEpisodeSource')
            pass

    def getLiveSource(self, name, genre, source, call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS rel_live (""source TEXT, ""imdb_id TEXT, ""season TEXT, ""episode TEXT, ""hosts TEXT, ""added TEXT, ""UNIQUE(source, imdb_id, season, episode, hosts)"");")
        except:
            pass

        logger.debug('Calling getLiveSource for %s' % call, __name__)
        retValue = 0
        retValue, srcs = call.livetv()
        logger.debug('Finished getLiveSource for %s' % call, __name__)
        if not name == None : name = name.upper()

        if retValue == 1:
            try:
                logger.debug('Updated file download from internet', __name__)
                dbcur.execute("DELETE FROM rel_live WHERE source = '%s' AND season = '%s'" % (source, 'live'))
                dbcon.commit()

                idx = 0
                for item in srcs:
                    poster = self.getLivePoster(item['name'])
                    if not poster == None :
                        item['poster'] = poster
                    else:
                        poster = item['poster']

                    #else:
                    #    item['poster'] = '0'
                    meta = {"poster":poster, "iconImage":poster, 'thumb': poster}
                    item['meta'] = json.dumps(meta)
                    if '||' in item['name']:
                        item['name'] = item['name'].split('||')[0]
                    dbcur.execute("INSERT INTO rel_live Values (?, ?, ?, ?, ?, ?)", (source, item['name'], 'live', str(idx), json.dumps(item), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                    idx = idx + 1
                    dbcon.commit()
            except Exception as e:
                logger.error(e.message)
                pass
        elif retValue == 0 and name != None:
            try:
                srcs = []
                dbcur.execute("SELECT * FROM rel_live WHERE source = '%s' AND imdb_id = '%s' AND season = '%s'" % (source, name, 'live'))
                for row in dbcur:
                    match = row
                    srcs = json.loads(match[4])
                    try :srcs['meta'] = json.loads(srcs['meta'])
                    except:pass
                    self.srcs.append(srcs)
                logger.debug('Fetched sources from cache for [%s]' % name, call.__class__)
                return self.srcs
            except:
                logger.debug('Source from cache not found for [%s]' % name, call.__class__)
                pass

        try:
            srcs = []
            if name == None or name == '':
                if genre == 'all':
                    query = "SELECT * FROM rel_live WHERE source = '%s' AND season = '%s'" % (source, 'live')
                elif genre == 'others':
                    query = "SELECT rel_live.* FROM rel_live WHERE source = '%s' AND season = '%s' AND rel_live.imdb_id NOT IN (SELECT name FROM live_meta)"  % (source, 'live')
                else :
                    query = "SELECT rel_live.* FROM rel_live, live_meta WHERE rel_live.imdb_id = live_meta.name AND source = '%s' AND season = '%s' AND live_meta.genre = '%s'" % (source, 'live',genre)
                dbcur.execute(query)
                for row in dbcur:
                    match = row[4]
                    self.srcs.append(json.loads(match))
                logger.debug('Fetched Live sources : %s' % len(self.srcs), call.__class__)
            else :
                dbcur.execute("SELECT * FROM rel_live WHERE source = '%s' AND imdb_id = '%s' AND season = '%s'" % (source, name, 'live'))
                for row in dbcur:
                    match = row
                    srcs = json.loads(match[4])
                    self.srcs.append(srcs)
            return self.srcs
        except Exception as e:
            logger.error('(%s) Exception Live sources : %s' % (call.__class__, e.args))
            pass

    def loadLiveMeta(self):
        control.makeFile(control.dataPath)
        self.sourceFile = control.sourcescacheFile
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DROP TABLE IF EXISTS live_meta")
            dbcur.execute("VACUUM")
            dbcon.commit()
        except:
            pass

        try:
            dbcur.execute("CREATE TABLE IF NOT EXISTS live_meta (""name TEXT, ""genre TEXT, ""lang TEXT, ""icon TEXT, ""alt_names TEXT, ""added TEXT, ""UNIQUE(name, genre, lang)"");")
        except:
            pass

        try :
            from ashock.modules import livemeta
            meta = livemeta.source().getLiveMeta()

            for item in meta:
                dbcur.execute("INSERT INTO live_meta Values (?, ?, ?, ?, ?, ?)", (item['name'], item['genre'], item['lang'], item['icon'], item['alt_names'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))

            dbcon.commit()
        except:
            import traceback
            traceback.print_exc()
            pass
        return 1

    def getLiveGenre(self):
        liveMeta = cache.get(self.loadLiveMeta, 72, table='live_cache')
        control.makeFile(control.dataPath)
        self.sourceFile = control.sourcescacheFile
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("SELECT distinct genre FROM live_meta order by genre")
            genre = []
            for row in dbcur:
                genre.append(row[0])
            return genre
        except:
            import traceback
            traceback.print_exc()
            pass

    def getLivePoster(self, source):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute("SELECT * FROM live_meta WHERE name = '%s'" % (source))
            match = dbcur.fetchone()
            poster_url = match[3]
            if poster_url == '':
                poster_url = None
            else :
                poster_url = os.path.join(control.logoPath(), poster_url)
            return poster_url
        except:
            pass

    def sourcesDialog(self, items):
        try:

            labels = [i['label'] for i in items]

            select = control.selectDialog(labels)
            if select == -1: return 'close://'

            next = [y for x,y in enumerate(items) if x >= select]
            prev = [y for x,y in enumerate(items) if x < select][::-1]

            items = [items[select]]
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog
            progressDialog.create(control.addonInfo('name'), '')
            progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    if items[i]['source'] == block: raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    try:
                        if progressDialog.iscanceled(): break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
                    except:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

                    m = ''

                    for x in range(3600):
                        try:
                            if xbmc.abortRequested == True: return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k: m += '1'; m = m[-1]
                        if (w.is_alive() == False or x > 30) and not k: break
                        time.sleep(0.5)


                    for x in range(30):
                        try:
                            if xbmc.abortRequested == True: return sys.exit()
                            if progressDialog.iscanceled(): return progressDialog.close()
                        except:
                            pass

                        if m == '': break
                        if w.is_alive() == False: break
                        time.sleep(0.5)


                    if w.is_alive() == True: block = items[i]['source']

                    if self.url == None: raise Exception()

                    self.selectedSource = items[i]['label']

                    try: progressDialog.close()
                    except: pass

                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')
                    return self.url
                except:
                    pass

            try: progressDialog.close()
            except: pass

        except Exception as e:
            logger.error(e.message)
            try: progressDialog.close()
            except: pass

    def sourcesDirect(self, items):

        u = None

        self.progressDialog = control.progressDialog
        self.progressDialog.create(control.addonInfo('name'), '')
        self.progressDialog.update(0)

        for i in range(len(items)):
            try:
                if self.progressDialog.iscanceled(): break

                self.progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))

                if xbmc.abortRequested == True: return sys.exit()

                url = self.sourcesResolve(items[i])
                if url == None: raise Exception()
                if u == None: u = url

                self.selectedSource = items[i]['label']
                self.progressDialog.close()

                return url
            except:
                pass

        try: self.progressDialog.close()
        except: pass

        return u

    def alterSources(self, url, meta):
        try:
            if control.setting('host_select') == '2': url += '&select=1'
            else: url += '&select=2'
            control.execute('RunPlugin(%s)' % url)
        except:
            pass

    def sourcesFilter(self):
        logger.debug('Calling sources.filter()', __name__)
        logger.debug('ORIGINAL SOURCE COUNT : %s' % len(self.srcs), __name__)
        for i in range(len(self.srcs)): self.srcs[i]['source'] = self.srcs[i]['source'].lower()
        self.srcs = sorted(self.srcs, key=lambda k: k['source'])

        originalSrcs = self.srcs

        quality = control.setting('playback_quality')
        if quality == '': quality = '0'

        #set content
        filter = []
        try:filter += [i for i in self.srcs if i['content'] == 'live']
        except:
            filter += [dict(i.items() + [('content', '')]) for i in self.srcs]
            self.srcs = filter

        filter = []
        #logger.debug(self.debridDict, __name__)
        #logger.debug(self.hostDict, __name__)
        #self.debridDict = {'premiumize': [], 'alldebrid': [], 'realdebrid': ['1fichier.com', 'alterupload.com', 'cjoint.net', 'desfichiers.com', 'dfichiers.com', 'megadl.fr', 'mesfichiers.org', 'piecejointe.net', 'pjointe.com', 'tenvoi.com', 'dl4free.com', '24uploading.com', '2shared.com', '4shared.com', 'alfafile.net', 'allmyvideos.net', 'anafile.com', 'catshare.net', 'cbs.com', 'clicknupload.me', 'clicknupload.com', 'clicknupload.link', 'cloudtime.to', 'divxstage.e', 'divxstage.to', 'dailymotion.com', 'datafile.com', 'datafilehost.com', 'datei.to', 'depfile.com', 'i-filez.com', 'dl.free.fr', 'easybytez.com', 'exashare.com', 'bojem3a.info', 'ajihezo.info', 'extmatrix.com', 'faststore.org', 'filefactory.com', 'fileflyer.com', 'fileover.net', 'filerio.com', 'filerio.in', 'filesabc.com', 'filesflash.com', 'filesflash.net', 'filesmonster.com', 'gigapeta.com', 'gigasize.com', 'gboxes.com', 'gulfup.com', 'hugefiles.net', 'hulkshare.com', 'keep2share.cc', 'k2s.cc', 'keep2s.cc', 'k2share.cc', 'kingfiles.net', 'load.to', 'mediafire.com', 'mega.co.nz', 'mega.nz', 'megashares.com', 'mightyupload.com', 'movshare.net', 'wholecloud.net', 'nitroflare.com', 'novamov.com', 'auroravid.to', 'nowdownload.e', 'nowdownload.ch', 'nowdownload.sx', 'nowdownload.ag', 'nowdownload.at', 'nowdownload.ec', 'nowdownload.li', 'nowdownload.to', 'nowvideo.e', 'nowvideo.ch', 'nowvideo.sx', 'nowvideo.ag', 'nowvideo.at', 'nowvideo.li', 'oboom.com', 'openload.co', 'openload.io', 'ozofiles.com', 'promptfile.com', 'sky.fm', 'radiotunes.com', 'rapidgator.net', 'rg.to', 'rarefile.net', 'redbunker.net', 'redtube.com', 'canalplus.fr', 'd8.tv', 'c8.fr', 'rockfile.e', 'rutube.r', 'salefiles.com', 'scribd.com', 'secureupload.e', 'sendspace.com', 'share-online.biz', 'solidfiles.com', 'soundcloud.com', 'streamin.to', 'thevideo.me', 'turbobit.net', 'tusfiles.net', 'ulozto.net', 'uloz.to', 'ulozto.sk', 'unibytes.com', 'uplea.com', 'upload.af', 'uploadable.ch', 'bigfile.to', 'uploadc.com', 'uploadc.ch', 'uploaded.net', 'uploaded.to', 'ul.to', 'uploading.com', 'uploadrocket.net', 'uploadx.org', 'upstore.net', 'uptobox.com', 'uptostream.com', 'userporn.com', 'userscloud.com', 'veevr.com', 'videoweed.es', 'bitvid.sx', 'vimeo.com', 'wipfiles.net', 'worldbytez.com', 'youporn.com', 'youtube.com', 'youwatch.org', 'chouhaa.info', 'sikafika.info', 'yunfile.com', 'filemarkets.com', '5xpan.com', 'dix3.com', 'zippyshare.com'], 'rpnet': []}
        #self.hostDict = ['wholecloud.net', 'vidzi.tv', 'watchers.to', 'videoraj.to', 'mersalaayitten.co', 'gorillavid.in', 'cloudy.sx', 'noslocker.com', 'divxstage.to', 'desiflicks.com', 'yourupload.com', 'streamcloud.eu', 'videoweed.es', 'nowvideo.at', 'letwatch.to', 'clicknupload.me', 'xvidstage.com', 'playpanda.net', 'cloudy.ch', 'stagevu.com', 'videoapi.my.mail.ru', 'mp4upload.com', 'vshare.eu', 'exashare.com', 'watchvideo10.us', 'allmyvideos.net', 'apnasave.in', 'uploadx.org', 'tune.pk', 'xpressvids', 'daclips.in', 'videoraj.com', 'playwire.com', 'usersfiles.com', 'vidup.org', 'my.mail.ru', 'streamin.to', 'vidlox.tv', 'vidmad.net', 'vivo.sx', 'watchvideo.us', 'youwatch.org', 'www.playhd.fo', 'nosvideo.com', 'ok.ru', 'vimeo.com', 'rapidvideo.com', 'watchvideo4.us', 'speedplay3.pw', 'byzoo.org', 'zstream.to', 'playu.me', 'nowvideo.fo', 'vidgg.to', 'powerwatch.pw', 'watchvideo7.us', 'watchvideo8.us', 'vidspot.net', 'videorev.cc', 'thevideobee.to', 'api.video.mail.ru', 'watchvideo3.us', 'dailymotion.com', 'novamov.com', 'filepup.net', 'uptobox.com', 'fileweed.net', 'idowatch.us', 'watchvideo2.us', 'jetload.tv', 'vid.me', 'trollvid.net', 'googleusercontent.com', 'mp4edge.com', 'video.tt', 'weshare.me', 'streame.net', 'veoh.com', 'speedplay1.site', 'uploadc.com', 'movshare.net', 'letwatch.us', 'mp4engine.com', 'indavideo.hu', 'videohut.to', 'happystreams.net', 'userscloud.com', 'videoraj.eu', 'play44.net', 'get.google.com', 'openload.co', 'dittotv.com', 'nowvideo.li', 'teramixer.com', 'toltsd-fel.tk', 'docs.google.com', 'vidcrazy.net', 'odnoklassniki.ru', 'videoraj.ec', 'yucache.net', 'mail.ru', 'shared.sx', 'vidbull.com', 'promptfile.com', 'filehoot.com', 'shitmovie.com', 'tvlogy.to', 'bitvid.sx', 'drive.google.com', 'movdivx.com', 'allvid.ch', 'myvidstream.net', 'watchvideo6.us', 'vshare.io', 'fastplay.cc', 'clicknupload.link', 'grifthost.com', 'vidto.me', 'nowvideo.eu', 'uploadcrazy.net', 'chouhaa.info', 'upload.af', 'youtu.be', 'auroravid.to', 'videoraj.co', 'videoraj.ch', 'nowvideo.ec', 'megamp4.net', 'playedto.me', 'rutube.ru', 'speedplay.pw', 'speedvideo.net', 'idowatch.net', 'briskfile.com', 'auengine.com', 'hugefiles.net', 'watchvideo5.us', 'dynns.com', 'everplay.watchpass.net', 'videoraj.sx', 'videozoo.me', 'watchvideo9.us', 'vk.com', 'kingfiles.net', 'thevideo.me', 'cloudy.com', 'vkpass.com', 'nowvideo.sx', 'youtube.com', 'cloudzilla.to', 'daclips.com', 'mp4stream.com', 'mersalaayitten.com', 'vidfile.xyz', 'speedplay.xyz', 'movpod.net', 'clicknupload.com', 'nowvideo.co', 'divxstage.eu', 'playbb.me', 'nowvideo.ch', 'videowing.me', 'flashx.tv', 'plus.google.com', 'movpod.in', 'openload.io', 'facebook.com', 'uptostream.com', 'divxstage.net', 'estream.to', 'video44.net', 'youlol.biz', 'cloudy.eu', 'videowood.tv', 'uploadc.ch', 'watchonline.to', 'rapidvideo.ws', 'neodrive.co', 'castamp.com', 'tamildrive.com', 'easyvideo.me', 'cloudy.ec', 'www.playhd.video', 'tusfiles.net', 'googlevideo.com', 'speedplay.us', 'zalaa.com', 'cloudtime.to', 'vodlocker.com', 'storeinusa.com', 'playu.net', 'videoweed.com', 'fastplay.sx', 'googledrive.com', 'thevideos.tv', 'gorillavid.com', 'vidup.me', 'vidshare.us']

        if debrid.status() == True:
            for d in self.debridDict: filter += [dict(i.items() + [('debrid', d)]) for i in self.srcs if i['source'].lower() in self.debridDict[d]]
            for host in self.hostDict : filter += [i for i in self.srcs if i['source'] in host and not i['content'] == 'live' and 'debridonly' not in i and i['source'] not in self.hostprDict]
        else :
            for host in self.hostDict : filter += [i for i in self.srcs if i['source'] in host and not i['content'] == 'live' and 'debridonly' not in i]

        filter += [i for i in self.srcs if i['direct'] == True and not i['content'] == 'live']
        try:filter += [i for i in self.srcs if i['content'] == 'live']
        except:pass
        self.srcs = filter

        logger.debug('FINAL SOURCE COUNT : %s' % len(self.srcs), __name__)

        random.shuffle(self.srcs)

        filter = []
        if quality == '0' : filter += [i for i in self.srcs if i['quality'] == '1080p' and 'debrid' in i]
        if quality == '0' : filter += [i for i in self.srcs if i['quality'] == '1080p' and not 'debrid' in i]
        if quality == '0' or quality == '1': filter += [i for i in self.srcs if i['quality'] == 'HD' and 'debrid' in i]
        if quality == '0' or quality == '1': filter += [i for i in self.srcs if i['quality'] == 'HD' and not 'debrid' in i]
        filter += [i for i in self.srcs if i['quality'] == 'SD' and not 'debrid' in i]
        if len(filter) < 35: filter += [i for i in self.srcs if i['quality'] == 'SCR']
        if len(filter) < 35:filter += [i for i in self.srcs if i['quality'] == 'CAM']
        if len(filter) < 35:filter += [i for i in self.srcs if i['quality'] == '']
        self.srcs = filter

        r = [x for x in self.srcs + originalSrcs if x not in self.srcs or x not in originalSrcs]

        logger.debug('Filtered Sources : %s' % r, __name__)

        for i in range(len(self.srcs)):

            s = self.srcs[i]['source'].lower()
            p = self.srcs[i]['provider']
            p = re.sub('v\d*$', '', p)

            q = self.srcs[i]['quality']

            try: f = (' | '.join(['[I]%s [/I]' % info.strip() for info in self.srcs[i]['info'].split('|')]))
            except: f = ''

            try: d = self.srcs[i]['debrid']
            except: d = self.srcs[i]['debrid'] = ''

            if not d == '': label = '%02d | [I]%s[/I] | [B]%s[/B] | ' % (int(i+1), d, p)
            else: label = '%02d | [B]%s[/B] | ' % (int(i+1), p)

            if q in ['1080p', 'HD']: label += '%s | %s | [B][I]%s [/I][/B]' % (s.rsplit('.', 1)[0], f, q)
            #elif q == 'SD': label += '%s | %s' % (s.rsplit('.', 1)[0], f)
            else: label += '%s | %s | [I]%s [/I]' % (s.rsplit('.', 1)[0], f, q)
            label = label.replace('| 0 |', '|').replace(' | [I]0 [/I]', '')
            label = label.replace('[I]HEVC [/I]', 'HEVC')
            label = re.sub('\[I\]\s+\[/I\]', ' ', label)
            label = re.sub('\|\s+\|', '|', label)
            label = re.sub('\|(?:\s+|)$', '', label)

            pts = None
            try : pts = self.srcs[i]['parts']
            except:pass

            if not pts == None and int(pts) > 1:
                label += ' [%s]' % pts

            self.srcs[i]['label'] = label.upper()
        return self.srcs

    def sourcesResolve(self, item):
        try:
            logger.debug('selected url : %s' % item['url'], __name__)
            logger.debug('selected item : %s' % item, __name__)
            u = url = item['url']
            provider = item['provider'].lower()


            d = item['debrid'] ; direct = item['direct']

            if not d == '':
                logger.debug('DEBRID : Resolving debrid', __name__)
                u = debrid.resolve(url, d)
                logger.debug('RESOLVED DEBRID : %s' % u, __name__)

            if d == '' or u == False :
                logger.debug('Resolving through provider', __name__)

                source = __import__(provider, globals(), locals(), [], -1).source()
                u = source.resolve(url, self.resolverList)
                if 'plugin.video.f4mTester' in u:
                    try :
                        title = item['name']
                        title = urllib.quote_plus(title.encode('utf-8'))
                        iconImage = item['poster']
                    except:
                        pass
                    u += '&name=%s&iconImage=%s' % (title, iconImage)
                logger.debug('Resolved through provider [%s]' % u, __name__)
                if u == False: raise Exception()

            url = u
            try :
                ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            except :
                ext = None
            if ext == 'rar': raise Exception()

            self.url = url
            return url
        except:
            self.url = None
            return

    def getResolverList(self):
        try:
            import urlresolver
            resolverList = []
            try: resolverList = urlresolver.relevant_resolvers(order_matters=True)
            except: resolverList = urlresolver.plugnplay.man.implementors(urlresolver.UrlResolver)
            resolverList = [i for i in resolverList if not '*' in i.domains]
        except:
            resolverList = []
        return resolverList

    def getHostDict(self):
        try:
            hostDict = [i.domains for i in self.resolverList]
            hostDict = [i.lower() for i in reduce(lambda x, y: x+y, hostDict)]
            hostDict = [x for y,x in enumerate(hostDict) if x not in hostDict[:y]]

            customHostDict = [x['host'] for x in resolvers.info()]
            customHostDict = [i.lower() for i in reduce(lambda x, y: x+y, customHostDict)]
            customHostDict = [x for y,x in enumerate(customHostDict) if x not in customHostDict[:y]]
            hostDict += customHostDict
            hostDict = list(set(hostDict))
        except:
            hostDict = []
        return hostDict

    def getHostPrDict(self):
        hostPrDict = ['dailymotion.com', 'openload.co']
        return hostPrDict
