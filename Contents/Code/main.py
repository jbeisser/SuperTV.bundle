#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib, urllib2, cookielib, threading
import string, os, re, time, datetime, sys, platform

from aes import AESCtr
from epg import *
#from main2 import *

try:
    from xml.etree import ElementTree
except:
    try:
        from elementtree import ElementTree
    except:
        pass

            
    def listLanguages(BASE, src):
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

        languages = list(set(languages))
        languages.sort()

        return languages