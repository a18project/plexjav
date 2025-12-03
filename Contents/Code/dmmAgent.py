# -*- coding: utf-8 -*-
import urllib
import urllib2
import re
import ssl
from datetime import datetime
from lxml import html

SEARCH_URL = 'https://www.dmm.co.jp/search/=/searchstr=%s/limit=10/sort=date/'
curID = "dmm"
imgProxy = 'http://192.168.1.11:8282/insecure/rs:fill:380:536/g:ea/plain/'

def getElementFromUrl(url):
    return html.fromstring(unicode(request(url)))

def request(url):
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent, 'Cookie':'age_check_done=1'}
    Log('Requesting: %s' % url)
    request = urllib2.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib2.urlopen(request, context=ctx).read()

def elementToString(ele):
    html.tostring(ele, encoding='unicode')

def search(query, results, media, lang):
    #Log(getElementFromUrl(SEARCH_URL % query))
    try:
        Log('Search Query: %s' % query)
        for movie in getElementFromUrl(SEARCH_URL % query).xpath('//p[contains(@class,"tmb")]'):
            movieurl = movie.xpath('.//a')[0].get('href').split('/?i')[0]
            movieid = str(movieurl).split("cid=")[1].upper()
            score = 100-3*Util.LevenshteinDistance(query,movieid)
            title = movie.xpath('.//span[@class="txt"]')[0].text_content().strip()
            Log('Search Result: id: %s' % movieid)
            Log(str(movieurl).replace('/','_x_').replace('=','_d_'))
            movieurl = str(movieurl).replace('/','_x_').replace('=','_d_')
            results.Append(MetadataSearchResult(id = curID + "|" + str(movieurl) + "|" + str(media.filename),
                                                name=str(movieid + " " + title + " - dmm"),
                                                score=score,lang=lang
                                                ))
        results.Sort('score', descending=True)
        Log(results)
    except Exception as e: Log(e)

def update(metadata, media, lang):
    if curID != str(metadata.id).split("|")[0]:
        return
    metadata.id = metadata.id.replace('_x_','/').replace('_d_','=')
    Log("Begin UPDATE")
    url = str(metadata.id).split("|")[1]
    Log('Update Query: %s' % url)
    
    url = "https://www.dmm.co.jp/age_check/=/declared=yes/?{}".format(urllib.urlencode({"rurl": url}))
    
    try:
        movie = getElementFromUrl(url).xpath('//div[contains(@class,"page-detail")]')[0]
        
        #ID
        movieid = re.sub('(\d{0,4})([A-z]+)(0*)(\d{3,5})',r'\2-\4',(metadata.id).split("|")[1].split('cid=')[1]).upper()
        Log(movieid)

        #Title
        title = movie.xpath('//h1[@id="title"]')[0].text_content()
        metadata.title = movieid + " " + title
        
        #COVER
        image = movie.xpath('//a[@name="package-image"]')[0]
        thumbUrl = imgProxy + image.get('href')
        thumb = request(thumbUrl)
        posterUrl = imgProxy + image.get('href')
        metadata.posters[posterUrl] = Proxy.Preview(thumb)

        #Actor
        for actor in movie.xpath('//span[@id="performer"]/a/text()'):
            Log(actor)
            role = metadata.roles.new()
            role.name = actor
            metadata.collections.add(role.name)

        cells = movie.xpath('//td[contains(@class,"nw")]/..')
        #search1 = "\u30ec\u30fc\u30d9\u30eb"
        for cell in cells :
            cell = cell.text_content()
            cell = re.sub('\n','',cell)
            #Log(cell)
        # Date
            if cell.find('発売日') != -1 :
                moviedate = re.sub('\D','',cell)
                Log(moviedate)
                metadata.originally_available_at = datetime.strptime(
                moviedate, '%Y%m%d')
                metadata.year = metadata.originally_available_at.year
                Log('Found Date: %s' % metadata.originally_available_at)
        # studio
            if cell.find('レーベル') != -1 :
                studio = re.sub('(^\s+|\s+$)', '', cell.split('：'.encode('utf-8'))[1])
                Log('Studio Found: %s' % studio)
                metadata.studio = studio
        # Director
            if cell.find('監督') != -1 :
                metadata.directors.clear()
                director = metadata.directors.new()
                director.name = re.sub('(^\s+|\s+$)', '', cell.split('：'.encode('utf-8'))[1])
                Log('Director Found: %s' % director.name)
        # Tags
            if cell.find('ジャンル') != -1 :
                tags = re.sub('(^\s+|\s+$)', '', cell.split('：'.encode('utf-8'))[1])
                tags = tags.split(u'\xa0')
                if len(tags) > 1 :
                    Log("Getting tags")
                    metadata.genres.clear()
                    for tag in tags:
                        metadata.genres.add(tag)

        '''
        #Studio
        #search1 = unicode("メーカー","utf-8")
        search1 = "\xe3\x83\xac\xe3\x83\xbc\xe3\x83\x99\xe3\x83\xab".encode('utf-8')
        studio = movie.xpath('//td[contains(text(),search1)]/following-sibling::td/a/text()')[0]
        Log(studio)
        metadata.studio = studio

        #diret
        search2 = unicode("配信開始日","utf-8")
        res2 = movie.xpath('//td[contains(text(),search2)]/following-sibling::td/a/text()')[0]
        if res2:
            Log(res2)
            metadata.directors.clear()
            director = metadata.directors.new()
            director.name = res2
        '''
    except Exception as e: 
        Log(e)