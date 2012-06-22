# -*- coding: utf-8 -*-
import urllib, urllib2, cookielib, time, socket,gzip,StringIO,zlib,inspect,sys
from datetime import datetime, timedelta,tzinfo

try:
    import xml.etree.cElementTree as ElementTree
except:
    from xml.etree import ElementTree

from epg import *

BASE=[
u'http://supertv.3owl.com/USA.xml',
u'http://supertv.3owl.com/United%20Kingdom.xml',
u'http://supertv.3owl.com/Deutschland.xml',
#u'http://supertv.3owl.com/Espana.xml',
u'http://supertv.3owl.com/France.xml',
u'http://supertv.3owl.com/Italia.xml',
#u'http://supertv.3owl.com/Oesterreich.xml',
#u'http://supertv.3owl.com/Portugal.xml',
#u'http://supertv.3owl.com/Svizzera%20Schweiz%20Suisse.xml',
#u'http://supertv.3owl.com/Viet%20Nam.xml',
#u'http://apps.ohlulz.com/rtmpgui/list.xml',
#u'http://home.no/chj191/LiveTV.xml',
#'http://home.no/chj191/xxx.xml',
]

TITLE    = 'SuperTV'
ICON     = 'icon-default.png'

HTTP.CacheTime = 60*5

def Start():
  # Initialize the plug-in
  Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
  Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
 
  # Setup the default attributes for the ObjectContainer
  ObjectContainer.title1 = TITLE
  ObjectContainer.view_group = 'List'
 
  # Setup the default attributes for the other objects
  DirectoryObject.thumb = R(ICON)
  VideoClipObject.thumb = R(ICON)

@handler('/video/SuperTV', 'SuperTV')
def Main():
    objs=[]
    if len(BASE) < 2:
        return ListLanguages(0)
        
    for b in BASE:
        objs.append(DirectoryObject(
            key = Callback(ListLanguages, src=BASE.index(b)),
            title = urllib.unquote(b.split('/')[-1][:-4]).replace('Espana','España').replace('Viet Nam','Việt Nam').replace('Oesterreich','Österreich')
          ))

    oc = ObjectContainer(objects=objs)
    return oc

def ListLanguages(src):
    xml=getURL(BASE[src],None)
    tree = ElementTree.XML(xml)
    if len(tree.findall('channel')) > 0:
        return listChannels(src)
        
    streams = tree.findall('stream')
    languages = []
    for stream in streams:
        language = stream.findtext('language').strip().capitalize()
        if not language in languages and language.find('Link down') == -1:
            languages.append(language)

    if len(languages) < 2:
        return listVideos(src=src,lang=languages[0])

    languages = list(set(languages))
    languages.sort()

    Log(languages)
    objs = []
    for l in languages:
        objs.append(DirectoryObject(
            key = Callback(listVideos,src=src, lang=l),
            title = l
          ))

    oc = ObjectContainer(objects=objs)
    return oc

def listVideos(src=0, lang=0):
    boldStart = ''
    boldEnd   = ''
    #if Client.Platform == ClientPlatform.MacOSX:
    #    boldStart = '[B]'
    #    boldEnd   = '[/B]'
    
    xml=getURL(BASE[src],None)
    tree = ElementTree.XML(xml)
    if len(tree.findall('channel')) > 0:
        return listChannels(src)
        
    streams = tree.findall('stream')
    
    #dir = MediaContainer(title='SuperTV', title2=urllib.unquote(BASE[src].split('/')[-1][:-4]).replace('Espana','España').replace('Viet Nam','Việt Nam').replace('Oesterreich','Österreich'),view_group='InfoList')
    #objs = []
    oc = ObjectContainer(view_group='InfoList',title1='SuperTV', title2=urllib.unquote(BASE[src].split('/')[-1][:-4]).replace('Espana','España').replace('Viet Nam','Việt Nam').replace('Oesterreich','Österreich'))
    for stream in streams:
        language = stream.findtext('language').strip().capitalize()
        if language == lang and language.find('Link down') == -1:
            title = boldStart+stream.findtext('title')+boldEnd
            epgid=stream.findtext('epgid', default=None)
            subtitle=''
		
            
            rtmplink = stream.findtext('link')
            if rtmplink[:4] != "http":
                for l in stream.findall('backup'):
                    if l.findtext('link')[:4] == "http":
                        rtmplink = l.findtext('link')
                if rtmplink[:4] != "http":
                    continue
                    
            if epgid:
                ep=epgid.split(":")
                if ep[0] in EPGs.keys():
                    e=EPGs[ep[0]](ep[1])
                    hasEPG = True
                    desc = ''
                    epg=e.getEntries()
                    i=len(epg)
                    for e in epg:
                        desc += e[1].strftime("%I:%M")+'-'+e[2].strftime("%I:%M")+":\n"+e[0]+u"\n\n"
                    if len(epg) > 0:
                        title += ' - '+epg[0][0]
                    if len(epg) > 1:
                        subtitle = 'Next: '+epg[1][0]
                    
                    
                    
            #dir.Append(VideoItem(rtmplink, clip='', title=title, summary=desc, thumb=stream.findtext('logourl','')))
            vco = VideoClipObject(title = title, summary = desc, thumb = stream.findtext('logourl',''), url = rtmplink)
            vco.add(MediaObject(
              container = Container.MP4,
              video_codec = VideoCodec.H264,
              audio_codec = AudioCodec.AAC,
              audio_channels = 2,
              optimized_for_streaming = True,
              parts = [PartObject(key = rtmplink)]))
            oc.add(vco)
            #oc.add(VideoItem(rtmplink, clip='', title=title, summary=desc, thumb=stream.findtext('logourl','')))
            #if stream.findtext('playpath'):
            #    rtmplink += ' playpath='+stream.findtext('playpath').strip()
            #if stream.findtext('swfUrl'):
            #    rtmplink += ' swfurl='+stream.findtext('swfUrl').strip()
            #if stream.findtext('pageUrl'):
            #    rtmplink += ' pageurl='+stream.findtext('pageUrl').strip()
            #if stream.findtext('proxy'):
            #    rtmplink += ' socks='+stream.findtext('proxy').strip()
            #if stream.findtext('advanced','').find('live=') == -1 and rtmplink.find('mms://') == -1:
            #    rtmplink += ' live=1 '
            #rtmplink += ' '+stream.findtext('advanced','').replace('-v','').replace('live=1','').replace('live=true','')
            #Log(rtmplink)
            #dir.Append(VideoItem(url=rtmplink, title=title, thumb=stream.findtext('logourl'), art='',summary=desc))
    #return dir
    return oc