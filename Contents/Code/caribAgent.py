# -*- coding: utf-8 -*-
#import urllib
import urllib2
import re
import ssl
from datetime import datetime
from lxml import html

SEARCH_URL = "https://www.caribbeancompr.com/moviepages/%s/index.html"
curID = "carib"
imgProxy = ""

def getElementFromUrl(url):
    return html.fromstring(request(url).decode('euc-jp', errors="ignore"))

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
    html.decode(errors='ignore').tostring(ele, encoding='unicode')

def search(query, results, media, lang):
    try:
        Log('Search Query: %s' % str(SEARCH_URL % query))
        movie_id = re.match('[0-9]{6}[-_][0-9]{3}',query).group().replace("-","_")
        res = getElementFromUrl(SEARCH_URL % movie_id)
        score = 100
        title = res.xpath('//h1')[0].text_content().encode()
        movieurl = str(SEARCH_URL % movie_id).replace('/','_x_').replace('=','_d_').replace('?','_q_')
        results.Append(MetadataSearchResult(id = curID + "|" + str(movieurl) + "|" + str(media.filename).split("/")[-1],
                                            name=str("caribpr " + title),
                                            score=score,lang=lang
                                            ))            
        results.Sort('score', descending=True)
        for line in results:
           Log(line)
    except Exception as e: Log(e)

def update(metadata, media, lang):
    Log(str(metadata.id))
    if curID != str(metadata.id).split("|")[0]:
        Log("ID doesn't match")
        return
    metadata.id = metadata.id.replace('_x_','/').replace('_d_','=').replace('_q_','?')
    Log("Begin UPDATE")
    url = str(metadata.id).split("|")[1]
    Log('Update Query: %s' % url)
    try:
        movie = getElementFromUrl(url).xpath('//body')[0]
        
        #ID
        movieid = url.split("/index.html")[0].split("/")[-1]
        Log(movieid)

        #Title
        metadata.title = movie.xpath('//div[@class="heading"]//h1')[0].text_content()
                
        #COVER
        imageurl = url.split("index.html")[0] + "images/l_l.jpg"
        #if re.search("^//",imageurl):
        #    imageurl = "http:" + imageurl
        thumbUrl = imgProxy + imageurl
        thumb = request(thumbUrl)
        posterUrl = imgProxy + imageurl
        metadata.posters[posterUrl] = Proxy.Preview(thumb)
        
        #Actor
        for actor in movie.xpath('//ul/li[@class="movie-spec"]')[0].xpath('.//a/text()'):
            Log(actor)
            role = metadata.roles.new()
            role.name = actor
            metadata.collections.add(role.name)

        #Date
        moviedate = movieid.split("_")[0]
        metadata.originally_available_at = datetime.strptime(
                moviedate, '%m%d%y')
        metadata.year = metadata.originally_available_at.year
        Log('Found Date: %s' % metadata.originally_available_at)

        #Studio
        studio = "Caribbean"
        Log('Studio Found: %s' % studio)
        metadata.studio = studio

        #Director
        #director = movie.xpath('//div[@id="video_director"]//td//text()')[1]
        #if director:
        #    metadata.directors.clear()
        #    new_director = metadata.directors.new()
        #    new_director.name = director
        #Log('Director Found: %s' % new_director.name)

        #Tags
        tags = movie.xpath('//span[@class="spec-content"]//a[@class="spec-item"]/text()')
        Log(tags)
        if len(tags) > 1 :
            metadata.genres.clear()
            for tag in tags:
                metadata.genres.add(tag)
    except Exception as e: 
        Log(e)
