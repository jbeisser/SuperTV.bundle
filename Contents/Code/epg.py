#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib, urllib2, cookielib, time, USTimeZone,re,sqlite3,os,socket,gzip,StringIO,zlib,inspect,sys,HTMLParser
from datetime import datetime, timedelta,tzinfo

try: from xml.etree import ElementTree
except: from elementtree import ElementTree

try: import simplejson as json
except: import json

Eastern = USTimeZone.USTimeZone(-5, 'Eastern', 'EST', 'EDT')
Europe = USTimeZone.USTimeZone(+1, 'Europe', 'CET', 'CEST')
UK = USTimeZone.USTimeZone(0, 'Europe', 'GMT', 'BST')
Vietnam = USTimeZone.USTimeZone(7, 'Vietnam', 'VST', 'VDT')

LocalTimezone = USTimeZone.USTimeZone(((time.altzone+(time.daylight*3600))/3600)*(-1), 'Local', time.tzname[0], time.tzname[1])

try:
    import xbmcaddon
    EPGPATH = os.path.join(xbmcaddon.Addon(id='script.SuperTV').getAddonInfo('path'),'resources/SuperTV')
except:
    try:
        #Plexapp
        Log(os.getcwd())
        EPGPATH = 'SuperTV'
    except:
        EPGPATH = 'resources/SuperTV'

def enumerate(sequence, start=0):
    n = start
    toReturn = []
    for elem in sequence:
        toReturn += [(n, elem)]
        n += 1
    return toReturn
def decode (page):
    encoding = page.info().get("Content-Encoding")    
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        content = page.read()
        if encoding == 'deflate':
            data = StringIO.StringIO(zlib.decompress(content))
        else:
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
        page = data.read()
    else:
        page = page.read()

    return page
    
def getURL(url ,enc='utf-8',post=None,headers=None,ct=False):
    try:
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2;)'),('Accept-Encoding', 'gzip,deflate'),('Accept-Charset','utf-8')]
        if headers:
            opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2;)'),('Accept-Encoding', 'gzip,deflate'),('Accept-Charset','utf-8')]+headers
        if url[:7] == "file://":
            usock=open(url[7:],'r')
            response=usock.read()
        else:
            if ct:
                a={}
                for x in opener.addheaders:
                    a[x[0]] = x[1] 
                req = urllib2.Request(url, data=post, headers=a)
                usock = urllib2.urlopen(req)
                response=usock.read()
            else:
                usock=opener.open(url,post)
                response=decode(usock)
            usock.close()
        if not enc:
            return response
        return unicode(response, enc,errors='strict')
    except:
        return '<b></b>'

class downloadSocket:
    def __init__(self, host, port):
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))        

    def fetch(self, msg):
        self.sock.send(msg)
        return self.sock.makefile().read()
        

class BaseEPG:
    nocheck = False
    def onInit(self):
        pass
    def __init__(self,chan):
        frm = inspect.stack()
        if frm[1][3] != 'listVideos' and frm[2][1].split('/')[-1] != 'update.py':
            sys.exit(0)

        self.conn = sqlite3.connect(EPGPATH)
        c=self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='epg';")
        
        et=c.fetchone()
        if not et or et[0] == 0:
            c.execute('''create table epg
            (title text, start int, end int, description text, thumb text,
            chan text, module text)''')
        c.close()
        
        cn = chan.split('|')
        self.chan=cn[0]
        if 'nochk' in cn: self.nocheck = True
        self.onInit()
    
    def hasDetails(self,title,start,end):
        module=self.module
        c=self.conn.cursor()
        c.execute("SELECT thumb,description from epg WHERE title=? AND start=? AND end = ? AND chan = ? AND module = ?", (title, time.mktime(start.timetuple()), time.mktime(end.timetuple()), self.chan, module))
        e=c.fetchone()
        c.close()
        if e:
            return (e[0]!='',e[1]!='')
        else:
            return (False,False)
    
    def insertIntoDB(self, listOfEntries,au=False):
        module=self.module
        c=self.conn.cursor()
        for l in listOfEntries:
            c.execute("SELECT count(start) from epg WHERE title=? AND start=? AND end = ? AND chan = ? AND module = ?", (l[0], time.mktime(l[1].timetuple()), time.mktime(l[2].timetuple()), self.chan, module))
            e=c.fetchone()
            if not e or e[0] < 1 or e == None:
                desc = ''
                thumb = ''
                if len(l) > 3:
                    desc = l[3]
                if len(l) > 4:
                    thumb = l[4]
                c.execute("INSERT INTO epg VALUES (?,?,?,?,?,?,?);", (l[0], time.mktime(l[1].timetuple()), time.mktime(l[2].timetuple()) ,desc,thumb, self.chan, module))
                self.conn.commit()
            elif au:
                desc = l[0]
                thumb = 'NT'
                if len(l) > 3:
                    desc = l[3]
                if len(l) > 4:
                    thumb = l[4]
                    
                c.execute('UPDATE epg SET thumb=?, description=? WHERE title=? AND start=? AND end = ? AND chan = ? AND module = ?;', (thumb,desc,l[0], int(time.mktime(l[1].timetuple())), int(time.mktime(l[2].timetuple())), self.chan, module))                
                self.conn.commit()
        c.close()
        
    def fetchEPG(self,day=0,limit=5):
        c=self.conn.cursor()
        nowDateTime = datetime.now(LocalTimezone)+timedelta(days=day)
        module=self.module
        
        c.execute("SELECT * from epg WHERE module=? AND chan=? AND start > ? AND end > ? ORDER BY end LIMIT ?", (module,self.chan,time.mktime((nowDateTime-timedelta(days=1)).timetuple()),time.mktime(nowDateTime.timetuple()),limit))
        es=c.fetchall()
        c.close()
        return es
        
    def getEPGForDays(self,days=3,limit=5,next=0,au=False):
        if next < days:
            es=self.fetchEPG(next,limit)
            if len(es) < limit and ((not self.nocheck) or au):
                self.getList(self.chan,offset=next*(-1),au=au)
                self.getEPGForDays(limit=limit, days=days,next=next+1,au=au)
        else:
            return self.fetchEPG()
    
    def getEntries(self,limit=5,next=0):
        nowDateTime = datetime.now(LocalTimezone)
        self.update()
        self.getEPGForDays(1)
        es=self.fetchEPG(limit=limit)
        tepg=[]
        for l in es:
            start=nowDateTime.fromtimestamp(l[1],LocalTimezone)
            end=nowDateTime.fromtimestamp(l[2],LocalTimezone)
            tepg.append([l[0],start,end,l[3],l[4]])
        return tepg
        
        
    def update(self):
        nowDateTime = time.mktime(datetime.now(LocalTimezone).timetuple())
        c=self.conn.cursor()
        c.execute("DELETE FROM epg WHERE end < ?",(str(nowDateTime),))
        self.conn.commit()
        c.close()
        
def updateEPG(BASE):
    for source in BASE:
        xml=getURL(source,None)
        tree = ElementTree.XML(xml)
        streams = tree.findall('stream')
        for stream in streams:
            if stream.findtext('epgid'):
                ep=stream.findtext('epgid').split(":")
                if ep[0] in EPGs.keys():
    				print 'Updating '+ep[0]+' '+ep[1]
    				sys.stdout.flush()
    				EPGs[ep[0]](ep[1]).getEPGForDays(limit=100,au=True)
    
class TVGuideEPG(BaseEPG):
    module = 'TVGuideEPG'
    def getList(self,srcid,offset=0,next=None,au=False):
        listings=getURL("http://www.tvguide.com/listings/data/ajaxchan.ashx?srcid="+str(srcid)+"&days="+str((offset*(-1))+2))
        listings = listings.split('\n\n')[1:]
        listings = "\n".join(listings)
        listings=listings.split("\n")

        nl=[]
        for l in listings:
            if l:
                nl.append(l.split('\t'))
    
        nowDateTime = datetime.now(LocalTimezone)
        tepg = []
        for fL in nl:
            start=datetime.fromtimestamp(time.mktime(time.strptime(fL[14], "%Y%m%d%H%M"))).replace(tzinfo=Eastern)
            end=(start+timedelta(minutes=int(fL[15]))).replace(tzinfo=Eastern)
            
            start=start.astimezone(LocalTimezone)
            end=end.astimezone(LocalTimezone)
            
            if end < nowDateTime:
                continue
                
            hd = self.hasDetails(fL[4],start,end)
            if au and (not hd[0] or not hd[1]):
                details = getURL('http://www.tvguide.com/listings/data/detailcache.aspx?Qr='+fL[12]+'&tvoid='+fL[16]+'&flags=RC&v2=1')
                details = details.split('\t')
            
                desc = details[3].strip()
                thumb = details[16].strip()
                if not desc:
                    desc = fL[4]
                if not thumb:
                    thumb = 'NT'
            else:
                desc,thumb = ('','')
            
            if end > nowDateTime:
                tmp=[fL[4], start, end,desc,thumb]
                if not tmp in tepg:
                    tepg.append(tmp)

        self.insertIntoDB(tepg,au=au)

class TVProgramm24EPG(BaseEPG):
    module = 'TVProgramm24EPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Europe) - timedelta(days=offset)
        listings=getURL('http://www.tvprogramm24.com/'+tdate.strftime("%Y-%m-%d")+'/'+chan+'/index.html','latin_1')
        if not listings:
            return
        r = re.compile('<TR BGCOLOR=.*?><TD VALIGN=TOP><INPUT NAME=".*?" TYPE=CHECKBOX VALUE="(?P<startDate>.*?)"></TD><TD VALIGN=TOP>.*?</TD><TD VALIGN=TOP><A TITLE=".*?" HREF="(.*?)">(?P<title>.*?)</A><BR>.*?</TD><TD>.*?</TD></TR>')
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(l[0][:12], "%Y%m%d%H%M"))).replace(tzinfo=Europe)
            
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(listings[i+1][0][:12], "%Y%m%d%H%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime(listings[i][0][:8]+'2359', "%Y%m%d%H%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
            
            if end < datetime.now(Europe):
                continue
                
            hd = self.hasDetails(l[2],start,end)
            if au and (not hd[0] or not hd[1]):
                r=re.compile('<P>.*?<STRONG>(.*?)</STRONG>(.*?)</P>',re.DOTALL)
                details = getURL('http://www.tvprogramm24.com/'+l[1],'latin_1')
                try: 
                    desc = r.findall(details)[0]
                    if desc[1].strip().replace('\n',''):
                        desc = desc[0]+' '+HTMLParser.HTMLParser().unescape(desc[1].replace('<P>',"\n").replace('<STRONG>',"[B]").replace('</STRONG>','[/B]'))
                    else:
                        desc = desc[0]
                except: desc = l[2]
            else:
                desc = ''
            
            start = start.astimezone(LocalTimezone)
            tepg.append([l[2], start,end,desc,'NT'])
            
        if not next:
            self.getList(chan,offset=(-1), next=True)
        self.insertIntoDB(tepg,au=au)
        
class TeleboyEPG(BaseEPG):
    module = 'TeleboyEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Europe) - timedelta(days=offset)
        
        o=offset*(-1)
        if o == 0:
            dt='now'
        else:
            dt=str(o+1)+'days'
        listings=getURL('http://www.teleboy.ch/programm/?program_date='+dt+'&program_filter=station&program_wheel='+chan+'&program_lang=de','iso-8859-15')
        r = re.compile('data-id="(?P<date>.*?)"><strong>(?P<title>.*?)</strong></a><p class="listing_info no_padding">(?P<start>.*?) - (?P<end>.*?) ')
        
        tepg = []
        lis=r.findall(listings)
        for l in lis:
            start=datetime.fromtimestamp(time.mktime(time.strptime(l[0][:12], "%Y%m%d%H%M"))).replace(tzinfo=Europe)
            end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+l[3], "%Y %m %d %H:%M"))).replace(tzinfo=Europe)
            
            if int(end.hour) < int(start.hour):
                end += timedelta(days=1)

            start=start.astimezone(LocalTimezone)
            end=end.astimezone(LocalTimezone)
            
            tepg.append([l[1], start, end])
            
        self.insertIntoDB(tepg,au=au)
            

class RaiEPG(BaseEPG):
    module = 'RaiEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        if datetime.now(Europe).hour < 6:
            offset = offset - 1
        tdate = datetime.now(Europe) - timedelta(days=offset)
            
        listings=getURL('http://www.rai.it/dl/portale/html/palinsesti/guidatv/static/'+chan+'_'+tdate.strftime("%Y_%m_%d")+'.html')
        r = re.compile('<span class="ora">(?P<word>.*?)</span> <span class="info"><a.*?>(?P<wordi>.*?)</a></span>')
        
        tepg = []
        listings=r.findall(listings)[:-1]
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            if int(l[0][:2]) < 6:
                start += timedelta(days=1)

            start=start.replace(tzinfo=Europe).astimezone(LocalTimezone)
            
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
                if int(listings[i+1][0][:2]) < 6:
                    end += timedelta(days=1)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d 06:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
            
            tepg.append([l[1], start, end])
        
        self.insertIntoDB(tepg,au=au)
            
class MediasetEPG(BaseEPG):
    module = 'MediasetEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        xml=getURL('http://www.tv.mediaset.it/dati/palinsesto/palinsesto-mondotv.xml')
        tree = ElementTree.XML(xml)
        listings=[]
        for pmi in tree.find('guidatv').findall('programmi'):
            listings += listingDay.findall('programma')
        tepg=[]
        for i,l in enumerate(listings):
            if l.attrib.get('idref') == chan:
                start=datetime.fromtimestamp(time.mktime(time.strptime(l.attrib.get('timestamp'), "%Y%m%d%H%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
                
                if i+1 < len(listings):
                    end=datetime.fromtimestamp(time.mktime(time.strptime(listings[i+1].attrib.get('timestamp'), "%Y%m%d%H%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
                else:
                    end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d 06:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
                    
                tepg.append([l.attrib.get('titolo'), start,end])
        self.insertIntoDB(tepg,au=au)
#http://epgservices.sky.com/tvlistings-proxy/TVListingsProxy/init.json
class SkyUKEPG(BaseEPG):
    module = 'SkyUKEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(UK) - timedelta(days=offset)
        listings=getURL('http://epgservices.sky.com/tvlistings-proxy/TVListingsProxy/tvlistings.json?channels='+chan+'&time='+tdate.strftime("%Y%m%d0000")+'&dur=2160&detail=2')
        try:
            listings = json.loads(listings)["channels"]["program"]
        except:
            return
    
        tepg = []
        for l in listings:
            if l['scheduleStatus'] == 'FINISHED':
                continue

            start=tdate.fromtimestamp(int(l['start'][:-3]),UK)
            start=start.replace(tzinfo=UK)
            end=start+timedelta(minutes=(int(l['dur'])/60))                        
            
            if end < datetime.now(UK):
                continue
            
            if au and not self.hasDetails(l['title'],start,end)[0]:
                image = getURL('http://tv.sky.com/programme/detail/'+chan+'/'+l['eventid'])
                i = re.compile('<img class="show-image" src="(.*?)" width=".*?" alt=".*?"/>')

                try:
                    thumb = i.findall(image)[0]
                except:
                    thumb = 'NT'
            else:
                thumb = ''
            
            start=tdate.fromtimestamp(int(l['start'][:-3]),UK)
            start=start.replace(tzinfo=UK)
            end=start+timedelta(minutes=(int(l['dur'])/60))
            
            start=start.astimezone(LocalTimezone)
            end=end.astimezone(LocalTimezone)
            
            if 'shortDesc' in l:
                desc = l['shortDesc']
            else:
                desc = l['title']
            
            tepg.append([l['title'], start,end, desc,thumb])
        
        self.insertIntoDB(tepg,au=au)

class SkyItaliaEPG(BaseEPG):
    module = 'SkyItaliaEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Europe) - timedelta(days=offset)
        listings=getURL('http://guidatv.sky.it/app/guidatv/contenuti/data/grid/'+tdate.strftime("%y_%m_%d")+'/ch_'+chan+'.js')
        try:
            listings = json.loads(listings)["plan"]
        except:
            return
    
        tepg = []
        sd=False
        for l in listings:
            if l['id'] == '-1':
                continue
                
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l["starttime"], "%Y %m %d %H:%M"))).replace(tzinfo=Europe)
            if sd:
                start += timedelta(days=1)

            end=start+timedelta(minutes=int(l['dur']))
            
            if end.day != start.day:
                sd = True
            if end < datetime.now(Europe):
                continue
            
            start=start.astimezone(LocalTimezone)
            end=end.astimezone(LocalTimezone)
            
            
            hd = self.hasDetails(l['title'],start,end)
            if au and (not hd[0] or not hd[1]):
                details = json.loads(getURL('http://guidatv.sky.it/EpgBackend/event_description.do?eid='+l['id']))
                desc = details['description']
                try:
                    image = getURL("http://guidatv.sky.it/guidatv/programma/"+l['genre'].replace(' ','')+"/"+l['subgenre'].replace(' ','')+"/"+l['normalizedtitle']+"_"+l['pid']+".shtml?eventid="+l['id'],None)
                    i = re.compile('<div class="foto">.*?<img.*?src="(.*?)".*?>')
                    thumb = i.findall(image)
                    thumb = thumb[0].replace(' ', '%20')
                except:
                    try:
                        image = getURL("http://guidatv.sky.it/guidatv/programma/"+l['genre'].replace(' ','')+"/"+l['subgenre'].replace(' ','')+"/"+l['normalizedtitle']+"_"+l['pid']+"_MINI.shtml?eventid="+l['id'])
                        i = re.compile('<img width="255" src="(.*?)" alt=".*?" class="foto" />')
                        thumb = i.findall(image)[0]
                    except:
                        thumb = 'http://guidatv.sky.it/app/guidatv/images'+details['thumbnail_url']
            else:
                thumb,desc = ('','')

            tepg.append([l['title'], start, end,desc, thumb])
        
        self.insertIntoDB(tepg,au=au)
        
class GuideTeleEPG(BaseEPG):
    module = 'GuideTeleEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        if datetime.now(Europe).hour < 4:
            offset = offset - 1
        tdate = datetime.now(Europe) - timedelta(days=offset)
        listings=getURL('http://telepoche.guidetele.com/programmes-tv/chaine/'+chan+'/hertziennes/soiree/'+tdate.strftime("%Y-%m-%d"))
        r = re.compile("<a.*?href=\"(.*?)\".*?showmenu\('(?P<start>.*?)-(?P<end>.*?)<br />.*?','(?P<title>.*?)'\)",re.DOTALL)

        tepg = []
        lis=r.findall(listings)
        for i,l in enumerate(lis):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[1], "%Y %m %d %Hh%M"))).replace(tzinfo=Europe)
            if int(start.hour) < 4 and i != 0:
              start += timedelta(days=1)
            end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+l[2], "%Y %m %d %Hh%M"))).replace(tzinfo=Europe)
            
            if int(end.hour) < int(start.hour):
                end += timedelta(days=1)

            if end < datetime.now(Europe):
                continue
                
            hd = self.hasDetails(l[3].replace('\\','').split(' - ')[0],start,end)
            if au and (not hd[0] or not hd[1]):
                t = re.compile('<td  style="width:.*?px" valign="top"><img src="(.*?)" alt=".*?"/></td>',re.DOTALL)
                d = re.compile('<td class="bleuf11r">(.*?)</td>',re.DOTALL)
                sd= re.compile('<table width="298" border="0" cellpadding="4" cellspacing="0" style="background-color:#FFF">(.*?)</table>',re.DOTALL)
                details = getURL('http://telepoche.guidetele.com'+l[0])
                try:
                    thumb = 'http://telepoche.guidetele.com'+t.findall(details)[0]
                except:
                    thumb = 'NT'
                try:
                    desc = d.findall(details)[0].strip()
                    if not desc:
                        desc = sd.findall(details)[0].strip()
                    
                except:
                    desc = l[3]
                desc = desc.replace('\n','')
                desc = desc.replace('\t','')
                desc = re.sub('<span class="bleuf11">(.*?)</span>',r'[B]\1[/B]',desc)
                desc = re.sub('<span class="bleuf11r">(.*?)</span>',r'\1',desc)
                desc = re.sub('<b>(.*?)</b>',r'[B]\1[/B]',desc)
                desc = re.sub('<strong>(.*?)</strong>',r'[B]\1[/B]',desc)
                desc = desc.replace('<br>','\n')
                desc = desc.replace('<br/>','\n')
                desc = desc.replace('<br />','\n')
                desc = desc.replace('<td style="width:266px" valign="top" class="bleuf11r">','')
                desc = desc.replace('<td colspan="2">','')
                desc = desc.replace('</td>','')
                desc = desc.replace('<tr>','')
                desc = desc.replace('</tr>','')
                desc = desc.replace(' :',':')

            else:
                desc, thumb = ('','')
            

            start=start.astimezone(LocalTimezone)
            end=end.astimezone(LocalTimezone)
            
            tepg.append([l[3].replace('\\','').split(' - ')[0], start, end,desc,thumb])
            
        self.insertIntoDB(tepg,au=au)
                
#http://www.plus.es/modulo/index.html?params=fecha%3D06032012%26hora%3D0715%26cadenas%3DTVE%26vista%3Dampliada%26modulo%3DGUIParrilla
class ElMundoESEPG(BaseEPG):
    module = 'ElMundoESEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        listings=getURL('http://estaticos.elmundo.es/elmundo/television/guiatv/js_parrilla/'+chan+'.js',enc='latin_1')
        r = re.compile('Programa.*?"(?P<title>.*?)", ".*?", "(?P<start>.*?)", "(?P<end>.*?)", ".*?", ".*?", ".*?", ".*?", ".*?", "(.*?)"')

        tepg = []
        lis=r.findall(listings)
        for i,l in enumerate(lis):
            start=datetime.fromtimestamp(float(l[1])).replace(tzinfo=LocalTimezone)
            end=datetime.fromtimestamp(float(l[2])).replace(tzinfo=LocalTimezone)
            if end < datetime.now(LocalTimezone):
                continue
            
            hd = self.hasDetails(l[0],start,end)
            if au and (not hd[0] or not hd[1]):
                details = getURL('http://www.elmundo.es'+l[3], enc='latin_1')
                i=re.compile('<div class="foto">.*?<img src="(.*?)" />.*?</div>',re.DOTALL)
                i = i.findall(details)
                d=re.compile('</div>.*?<p>(.*?)</p>.*?</div>.*?<div class="rompedor">',re.DOTALL)
                d = d.findall(details)
                try: thumb = i[0]
                except: thumb = 'NT'
                try: desc = d[0]
                except: desc = l[0]
            else:
                thumb,desc = ('','')
            tepg.append([l[0], start, end,desc,thumb])
            
        self.insertIntoDB(tepg,au=au)
        
class MeoPTEPG(BaseEPG):
    module = 'MeoPTEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Europe) - timedelta(days=offset)
        listings=getURL('http://www.meo.pt/ver/tv/guiatv/Pages/default.aspx?Channel='+chan+'&date='+tdate.strftime("%m-%d-%Y&time=%H:00"))
        r = re.compile('<div class="list_prog_hor">(?P<dt>.*?)</div><div.*?>.*?<a href="(.*?)".*?<span>.*? - (?P<title>.*?)</span>(?P<desc>.*?)</a></div>')

        tepg = []
        lis=r.findall(listings)
        for i,l in enumerate(lis):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Europe)
            if i+1 < len(lis):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+lis[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Europe).astimezone(LocalTimezone)
            start=start.replace(tzinfo=Europe).astimezone(LocalTimezone)
            tepg.append([l[2], start, end,l[3]])
            
        self.insertIntoDB(tepg,au=au)
        
class VTVVNEPG(BaseEPG):
    module = 'VTVVNEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        listings=getURL('http://vtv.vn/LichPS/GetLichPhatsong?nam='+str(tdate.year)+'&thang='+str(tdate.month)+'&ngay='+str(tdate.day)+'&kenh='+chan)#VTV2')
        r = re.compile('<tr>.*?<td.*?vtv-dskenh.*?<strong><nobr>(?P<dt>.*?)</nobr>.*?<td.*?strong>(?P<genre>.*?)</strong>.*?br />(?P<title>.*?)</td>',re.DOTALL)
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %Hh : %M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %Hh : %M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 12:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            title=l[1]
            if l[2].strip():
                #title=l[1].strip()+': '+l[2].strip()
                title = l[2].strip()
            tepg.append([title, start, end])
            
        self.insertIntoDB(tepg,au=au)
        
class BTVVNEPG(BaseEPG):
    module = 'BTVVNEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        
        listings=getURL('http://www.btv.org.vn/vi/schedule.html',post=urllib.urlencode({'datepicker':date.strftime("%d/%m/%Y"), 'channelid':chan}))
        r = re.compile("<tr bgcolor=.*?<.*?>(?P<dt>.*?)</td>.*?>(?P<genre>.*?)</td>.*?>(?P<title>.*?)</td>",re.DOTALL)
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            title=l[1]
            if l[2]:
                title=l[2]
            tepg.append([title, start, end])    
        self.insertIntoDB(tepg,au=au)
#621 - 17/1/2012
#%j
class BTTVVNEPG(BaseEPG):
    module = 'BTTVVNEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        a=int(tdate.strftime("%j"))+613+(365*(2012-tdate.year))+((2012-tdate.year)/4)
        
        listings=getURL('http://www.bttv.org.vn/index.php?btv=lichphatsong&sub=lichtruyenhinh&lichngayid='+str(a))
        r = re.compile('<div class="list-item"> <span style="color: Red">(?P<dt>.*?)</span>&nbsp;(?P<title>.*?)</div>')
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            tepg.append([l[1], start, end])    
        self.insertIntoDB(tepg,au=au)

#http://www.vtc.com.vn/Schedule.aspx?lpid=10&date=3/2/12
"""<select name="cbLiveProgram" id="cbLiveProgram" class="textbox">
	<option value="10">VTC1</option>
	<option value="11">VTC2</option>
	<option value="20">VTC 8</option>
	<option value="21">VTC 9</option>
	<option value="22">VTC10</option>
	<option value="5">HTV</option>
	<option value="24">HTV7</option>
	<option value="4">HTV9</option>
	<option value="15">VTV1</option>
	<option value="23">VTV2</option>
	<option value="3">VTV3</option>
	<option value="2">VTV4</option>
	<option value="29">VOV1</option>
	<option value="28">VOV2</option>
	<option value="27">VOV3</option>
	<option value="17">VTC11</option>
</select>"""
class VTCVNEPG(BaseEPG):
    module = 'VTCVNEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        listings=getURL('http://www.vtc.com.vn/Schedule.aspx?lpid='+chan+'&date='+tdate.strftime("%m/%d/%Y"))
        r = re.compile("<tr><td height='40' width=70 align='center' class='ScheduleKenh'>(?P<dt>.*?)</td><td class='ScheduleCurent'>(?P<title>.*?)</td></tr>")
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %I:%M:%S %p")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %I:%M:%S %p"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 12:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            tepg.append([l[1].replace('<br><b>',' -').replace('</b>',''), start, end])
            
        self.insertIntoDB(tepg,au=au)

class VTCVNHDEPG(BaseEPG):
    module = 'VTCVNHDEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        listings=getURL('http://hdtv.vtc.vn/Handler/getProgram.ashx?channel='+chan+'&dt='+tdate.strftime("%d-%m-%Y"))
        r = re.compile("<div class=\"list_kenh\"><span>(.*?)</span> &nbsp; (.*?)</div>",re.DOTALL)
        
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            t=''
            ls=l[1].split('\n')
            for lss in ls:
               t += lss.strip()+' ' 
            tepg.append([t, start, end])
            
        self.insertIntoDB(tepg,au=au)

"""        <select name="ctl06$ddlChannel" id="ctl06_ddlChannel" style="width:157px;">
        	<option selected="selected" value="7">SCTV1</option>
        	<option value="2">SCTV 2</option>
        	<option value="10">SCTV 3</option>
        	<option value="9">SCTV 4</option>
        	<option value="11">SCTV 5</option>
        	<option value="12">SCTV 6</option>
        	<option value="13">SCTV 7</option>
        	<option value="14">SCTV 8</option>
        	<option value="8">SCTV 9</option>
        	<option value="15">SCTV 10</option>
        	<option value="16">SCTV 11</option>
        	<option value="17">SCTV 12</option>
        	<option value="18">SCTV 13</option>
        	<option value="19">SCTV 14</option>
        	<option value="20">SCTV 15</option>
        	<option value="21">SCTV 16</option>
        	<option value="4">SCTV 17</option>
        	<option value="22">SCTV18</option>
        	<option value="23">HBO</option>
        	<option value="24">Cinemax</option>
        	<option value="25">ESPN</option>
        	<option value="26">STARMOVIES</option>
        	<option value="27">STARSPORTS</option>
        	<option value="28">STARWORLD</option>
        	<option value="34">VTV1</option>
        	<option value="29">VTV2</option>
        	<option value="30">VTV3</option>
        	<option value="32">CNN</option>
        	<option value="33">AXN</option>
        	<option value="35">VTV4</option>
        	<option value="31">VTV6</option>
        	<option value="36">VTV9</option>
        	<option value="37">HTV3</option>
        	<option value="38">HTV7</option>
        	<option value="39">HTV9</option>
        	<option value="40">Dong Nai 1</option>
        	<option value="41">LA34</option>
        	<option value="42">THVL1</option>
        	<option value="43">HA NOi 1</option>
        	<option value="44">ANTV</option>
        	<option value="45">THBThuan</option>

        </select>"""
class TV24VNEPG(BaseEPG):
    module = 'TV24VNEPG'
    viewstate = None
    def onInit(self):
        self.nocheck = True
        
    def getList(self,chan,offset=0,next=None,au=False):
        if not self.viewstate:
            tmp=getURL('http://tv24.com.vn')
            r=re.compile("<input type=\"hidden\" name=\"__VIEWSTATE\" id=\"__VIEWSTATE\" value=\"(.*?)\"",re.DOTALL)
            self.viewstate = r.findall(tmp)[0]

        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        post = urllib.urlencode({'__VIEWSTATE':self.viewstate, "__EVENTTARGET":"","__EVENTARGUMENT":''})
        post += '&ScriptManager1=ctl06$UpdBroadcast|ctl06$btnView'+'&ctl06_txtSearch_text=T%C3%ACm%20ch%C6%B0%C6%A1ng%20tr%C3%ACnh%20y%C3%AAu%20th%C3%ADch'
        post += '&ctl01$ctl01$txtUser=&ctl01_ctl01_txtUser_ClientState=%7B%22enabled%22%3Atrue%2C%22emptyMessage%22%3A%22T%C3%AAn%20%C4%91%C4%83ng%20nh%E1%BA%ADp%22%7D'
        post += '&ctl01_ctl01_txtPass_text=&ctl01$ctl01$txtPass=&ctl01_ctl01_txtPass_ClientState=&ctl02_cWindowThongBao_ClientState=&ctl02_RadWindowManager1_ClientState='
        post += '&ctl06_txtSearch_text=T%C3%ACm%20ch%C6%B0%C6%A1ng%20tr%C3%ACnh%20y%C3%AAu%20th%C3%ADch&ctl06$txtSearch='
        post += '&ctl06_txtSearch_ClientState=%7B%22enabled%22%3Atrue%2C%22emptyMessage%22%3A%22T%C3%ACm%20ch%C6%B0%C6%A1ng%20tr%C3%ACnh%20y%C3%AAu%20th%C3%ADch%22%7D'
        post += '&ctl06$ddlChannel='+chan+'&ctl06$ddlDay='+str(tdate.day)+'&ctl06$ddlMonth='+str(tdate.month)+'&ctl06$ddlYear='+str(tdate.year)+'&ctl06$btnView='
        
        listings=getURL('http://tv24.com.vn/default.aspx', post=post,headers=[('Referer','http://tv24.com.vn/'),('Origin','http://tv24.com.vn'),('X-MicrosoftAjax','Delta=true')])
        r = re.compile("<tr><td><b>(?P<dt>.*?)</b></td><td>(?P<title>.*?)</td></tr>",re.DOTALL)
        tepg = []
        listings=r.findall(listings)
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            t=''
            ls=l[1].split('\n')
            for lss in ls:
               t += lss.strip()+' ' 
            tepg.append([t, start, end])

        self.insertIntoDB(tepg,au=au)
        
class ITVVNEPG(BaseEPG):
    module = 'ITVVNEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        listings=getURL('http://itv.vn/Lichphatsong.aspx', post=urllib.urlencode({'hdnChannel':chan, 'hdnDate':tdate.strftime("%d/%m/%Y"), 'hdnlsAjax':'0'}))
        
        r1 = re.compile('class="Schedule_Text3">(?P<dt>.*?)</td>')
        r2 = re.compile('class="Schedule_Text4">(?P<title>.*?)</td>')

        tepg = []
        l1=r1.findall(listings)
        l2=r2.findall(listings)
        if not l1 or not l2:
            return
            
        listings=zip(l1,l2)
        listings=listings[1:]
        for i,l in enumerate(listings):
            start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
            start=start.replace(tzinfo=Vietnam)
            if i+1 < len(listings):
                end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            else:
                end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

            start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
            if l[1] != 'NNull':
                tepg.append([' '.join(l[1].split(':')[-1:]).strip(), start, end])
        self.insertIntoDB(tepg,au=au)
        
class HanoiTVEPG(BaseEPG):
    module = 'HanoiTVEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        listings=getURL('http://www.hanoitv.vn/Modules/TVSchedule/GenerateScheduleByChannel.aspx?cn='+chan)
        r1 = re.compile('<div id=.*?"t(?P<date>.*?).".*?pglist.*?>(?P<content>.*?)</div>')
        r2 = re.compile('<p.*?shd-item.*?time.*?> (?P<dt>.*?)</span>.*?program.*?>(?P<title>.*?)</span>.*?</p>')
        st = re.compile('<em>(.*?)</em>')
        
        l1=r1.findall(listings)
        
        if not l1:
            return
            
        tepg = []
        for l11 in l1:
            tdate=datetime.fromtimestamp(time.mktime(time.strptime(l11[0], "%d%m%Y"))).replace(tzinfo=Vietnam)
            listings=r2.findall(l11[1])
            for i,l in enumerate(listings):
                start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l[0], "%Y %m %d %H:%M")))
                start=start.replace(tzinfo=Vietnam)
                if i+1 < len(listings):
                    end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1][0], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
                else:
                    end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

                start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
                title = ''.join(l[1].decode('unicode_escape').split(':')[1:]).strip()
                stitle = st.findall(title)
                title = title.split('<')[0]
                if len(stitle) > 0:
                    title += ' - '+' - '.join(stitle)
                
                tepg.append([title, start, end])
        self.insertIntoDB(tepg,au=au)

class DongNaiEPG(BaseEPG):
    module = 'DongNaiEPG'
    def getList(self,chan,offset=0,next=None,au=False):
        tdate = datetime.now(Vietnam) - timedelta(days=offset)
        a=getURL('http://www.dnrtv.org.vn/WebServices/ChannelSchedulesWebService.asmx/GetChannelSchedules',post='{"type":1}',headers=[('Content-Type','application/json; charset=UTF-8'),('Origin','http://www.dnrtv.org.vn'),('Referer','http://www.dnrtv.org.vn')],ct=True)
        try:
            d=json.loads(a)['d']
        except:
            return
        for ds in d:
            if ds['ChannelName'][-1] != chan or ds['ScheduleDate'] != tdate.strftime("%d/%m/%Y"):
                continue
                
            listings=getURL('http://www.dnrtv.org.vn/WebServices/ChannelSchedulesWebService.asmx/GetScheduleDetails',post='{"sId":"'+str(ds['ScheduleId'])+'"}',headers=[('Content-Type','application/json; charset=UTF-8'),('Origin','http://www.dnrtv.org.vn'),('Referer','http://www.dnrtv.org.vn')],ct=True)
            listings=json.loads(listings)['d']
            tepg=[]
            for i,l in enumerate(listings):
                start=datetime.fromtimestamp(time.mktime(time.strptime(tdate.strftime("%Y %m %d ")+l['Time'], "%Y %m %d %H:%M")))
                start=start.replace(tzinfo=Vietnam)
                if i+1 < len(listings):
                    end=datetime.fromtimestamp(time.mktime(time.strptime(start.strftime("%Y %m %d ")+listings[i+1]['Time'], "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)
                else:
                    end=datetime.fromtimestamp(time.mktime(time.strptime((tdate+timedelta(days=1)).strftime("%Y %m %d 00:00"), "%Y %m %d %H:%M"))).replace(tzinfo=Vietnam).astimezone(LocalTimezone)

                start=start.replace(tzinfo=Vietnam).astimezone(LocalTimezone)
                tepg.append([l['Program'].strip(), start, end])
            self.insertIntoDB(tepg,au=au)
            return
        
EPGs = {'rai':RaiEPG, 'mediaset': MediasetEPG,'skyit':SkyItaliaEPG, 'skyuk': SkyUKEPG, 'teleboy':TeleboyEPG, 
        'tvprg24':TVProgramm24EPG, 'tvguide':TVGuideEPG, 'guidetele':GuideTeleEPG, 'vtc':VTCVNEPG, 'tv24vn':TV24VNEPG,
        'itvvn':ITVVNEPG, 'hanoitv':HanoiTVEPG, 'vtv':VTVVNEPG,'dongnai':DongNaiEPG,'btvvn':BTVVNEPG,'bttvvn':BTTVVNEPG,
        'vtchd':VTCVNHDEPG, 'elmundo':ElMundoESEPG, 'meo':MeoPTEPG}
