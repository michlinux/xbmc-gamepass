﻿import urllib
import os
import time
import sys
from datetime import datetime, timedelta
from traceback import format_exc
from urlparse import urlparse, parse_qs

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import StorageServer
import xmltodict

from game_common import *

addon = xbmcaddon.Addon()
addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
addon_profile = xbmc.translatePath(addon.getAddonInfo('profile'))
icon = os.path.join(addon_path, 'resources', 'gr_icon.png')
fanart = os.path.join(addon_path, 'resources', 'gr_fanart.jpg')
debug = addon.getSetting('debug')
cache = StorageServer.StorageServer("nfl_game_rewind", 2)
language = addon.getLocalizedString


def display_games(season, week_code):
    games = get_weeks_games(season, week_code)
    preferred_version = int(addon.getSetting('preferred_game_version'))
    # super bowl week has only one game, which thus isn't put into a list
    if isinstance(games, dict):
        games_list = [games]
        games = games_list

    if games:
        for game in games:
            duration = None
            mode = 4
            date_time_format = '%Y-%m-%dT%H:%M:%S.000'
            home_team = game['homeTeam']
            # sometimes the first item is empty
            if home_team['name'] is None:
                continue
            away_team = game['awayTeam']
            game_name = '%s %s at %s %s' %(away_team['city'], away_team['name'], home_team['city'], home_team['name'])

            game_ids = {}
            for i in ['condensedId', 'programId', 'id']:
                if game.has_key(i):
                    if 'condensed' in i:
                        label = language(30015)
                    elif 'program' in i:
                        label = language(30014)
                    else:
                        label = 'Live'
                    game_ids[label] = game[i]

            if not game.has_key('hasProgram'):
                # may want to change this to game['gameTimeGMT'] or do a setting maybe
                game_datetime = datetime(*(time.strptime(game['date'], date_time_format)[0:6]))
                game_date_string = game_datetime.strftime('%A, %b %d - %I:%M %p')
                game_name += ' - ' + game_date_string + ' ET'
                mode = 8
            if game.has_key('isLive'):
                # sometimes isLive lies
                if not game.has_key('gameEndTimeGMT'):
                    game_name += ' - Live'
            if game.has_key('gameEndTimeGMT'):
                try:
                    start_time = datetime(*(time.strptime(game['gameTimeGMT'], date_time_format)[0:6]))
                    end_time = datetime(*(time.strptime(game['gameEndTimeGMT'], date_time_format)[0:6]))
                    duration = (end_time - start_time).seconds / 60
                except:
                    addon_log(format_exc())

            add_dir(game_name, game_ids, mode, icon, '', duration, False)
    else:
        dialog = xbmcgui.Dialog()
        dialog.ok("Fetching Games Failed", "Fetching Game Data Failed.")
        addon_log('Fetching games failed.')

def display_seasons(seasons):
    for season in seasons:
        add_dir(season, season, 2, icon)

def display_weeks(season, weeks):
    for week_code, week_name in sorted(weeks.iteritems()):
        add_dir(week_name, season + ';' + week_code, 3, icon)

# seems a need to request before requesting encryptvideopath
def set_cookies(week, season):
    url = 'http://gamerewind.nfl.com/nflgr/servlets/games'
    post_data = {
        'isFlex': 'true',
        'week': week,
        'season': season
        }
    get_cookie = make_request(url, urllib.urlencode(post_data))
    if get_cookie:
        return True

def add_dir(name, url, mode, iconimage, discription="", duration=None, isfolder=True):
    params = {'name': name, 'url': url, 'mode': mode}
    url = '%s?%s' %(sys.argv[0], urllib.urlencode(params))
    listitem = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
    listitem.setProperty("Fanart_Image", fanart)
    if not isfolder:
        if not mode == 8:
            # IsPlayable tells xbmc that there is more work to be done to resolve a playable url
            listitem.setProperty('IsPlayable', 'true')
        listitem.setInfo(type="Video", infoLabels={"Title": name, "Plot": discription, "Duration": duration})
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, isfolder)

def get_params():
    p = parse_qs(sys.argv[2][1:])
    for i in p.keys():
        p[i] = p[i][0]
    return p


if debug == 'true':
    cache.dbg = True

params = get_params()
addon_log("params: %s" %params)

try:
    mode = int(params['mode'])
except:
    mode = None


if mode == None:
    auth = check_login()
    if auth:
        seasons = eval(cache.get('seasons'))
        display_seasons(seasons)
    else:
        dialog = xbmcgui.Dialog()
        dialog.ok("Error", "Could not acquire Game Rewind metadata.")
        addon_log('Auth failed.')
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 1:
    # unused for the time being
    # will be used later when/if NFL Network and NFL RedZone support is added
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 2:
    weeks = eval(cache.get('weeks'))
    season = params['name']
    display_weeks(season, weeks)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 3:
    season, week_code = params['url'].split(';', 1)
    display_games(season, week_code)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 4:
    try:
        if isinstance(eval(params['url']), dict):
            game_ids = eval(params['url'])
            game_id = game_ids['Full']
    except NameError:
        game_id = params['url']
    resolved_url = get_stream_url(game_id)
    addon_log('Resolved URL: %s.' %resolved_url)
    item = xbmcgui.ListItem(path=resolved_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

elif mode == 8:
    # for a do nothing list item
    pass

cache.set('mode', str(mode))