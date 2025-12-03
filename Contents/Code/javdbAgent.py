import urllib2
import urllib
import ssl
import re
import krequests
from datetime import datetime
from lxml import html


BASE_URL = 'http://javdb457.com'
SEARCH_URL = BASE_URL + '/search?q=%s'
curID = "javdb"
imgProxy = 'http://192.168.1.11:8282/insecure/rs:fill:380:536/g:ea/plain/'


def getElementFromUrl(url):
    return html.fromstring(unicode(request(url)))


def qqqrequest(url):
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent, }
    Log('Requested URL: %s' % url)
    request = urllib2.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    response = urllib2.urlopen(request, context=ctx).read()    
    return response

def request(url):
    response = krequests.get(url)    
    if response['success']:
        content = response['content']
        Log("Success! Used FlareSolverr:", response['used_flaresolverr'])
        Log("Status code:", response['status_code'])
        Log("Content length:", len(content))
        return content
    else:
        Log("Failed to get content:")
        Log("Error:", response['error'])
        Log("Used FlareSolverr:", response['used_flaresolverr'])
        Log("Cloudflare detected:", response['cloudflare_detected'])
        return None


def elementToString(ele):
    html.tostring(ele, encoding='UTF-8')


def search(query, results, media, lang):
    try:
        url = str(SEARCH_URL % urllib.quote_plus(query))
        res = request(url)
        Log(res)
    except Exception as e:
        Log(e)
    try:
        url = str(SEARCH_URL % urllib.quote_plus(query))
        res = getElementFromUrl(url)
        #Log(html.tostring(res,encoding='unicode'))
        for movie in res.xpath('//div[@class="item"]'):
            #Log(html.tostring(movie,encoding='unicode'))
            moviepath = movie.xpath('.//a')[0].get("href").replace('/', "__")
            movietitle = movie.xpath('.//a')[0].get("title")
            Log(movietitle)
            movieid = movie.xpath('.//strong')[0].text_content() or "000"
            if re.search(movieid,movietitle):
                resultname = movietitle + " " + curID 
            else:
                resultname = movieid + " " + movietitle +" "+  curID
            score=98-3*Util.LevenshteinDistance(query,movieid)
            results.Append(MetadataSearchResult(id=curID + "|" + str(moviepath)+ "|" + str(media.filename),
                                                name=resultname, score=score, lang=lang))
        results.Sort('score', descending=True)
        #Log(results)
    except Exception as e:
        Log(e)


def update(metadata, media, lang):
    Log(str(metadata.id))
    if curID != str(metadata.id).split("|")[0]:
        return

    query = str(metadata.id).split("|")[1].replace('__', '/', 4)
    Log('Update Query: ' + BASE_URL + str(query))
    try:
        movie = getElementFromUrl(BASE_URL + query + '?locale=zh').xpath('//section/div[@class="container"]')[0]

        # title
        metadata.title = " ".join(movie.xpath('.//h2')[0].text_content().replace("顯示原標題","-").split())

        # poster
        poster = movie.xpath('.//img[contains(@class,"video-cover")]')[0].get('src')
        thumbUrl = imgProxy + poster
        thumb = request(thumbUrl)
        posterUrl = imgProxy + poster
        metadata.posters[posterUrl] = Proxy.Preview(thumb)

        # actors
        actor_str = movie.xpath('.//strong[@class="symbol female"]/..')[0].text_content()
        re.sub('\n','',actor_str)
        Log(actor_str)
        matched = re.findall(unicode("(\S*)♀","utf-8"),actor_str,flags=re.UNICODE|re.MULTILINE)
        #Log(unicode(matched[0],"utf-8"))
        if matched:
            actors = matched
        if (len(actors)>0):
            metadata.roles.clear()
            for actor in actors:
                actor = actor.strip()
                role = metadata.roles.new()
                role.name = actor
                metadata.collections.add(role.name)
                Log(actor)
                strs = movie.xpath('.//strong[@class="symbol female"]/../a')
                for string in strs:
                    if string.text_content().find(actor) + 1 :
                        actorpage = BASE_URL + string.get('href')
                        Log(actorpage)
                        break
                avatar = getElementFromUrl(actorpage).xpath('//span[@class="avatar"]')
                if len(avatar)>0 :
                    role.photo = avatar[0].get('style').split("url(")[1].replace(")","")            

        # release date & year
        moviedate = movie.xpath('.//div[@class="panel-block"]/span')[0].text_content()
        metadata.originally_available_at = datetime.strptime(
            moviedate, '%Y-%m-%d')
        metadata.year = metadata.originally_available_at.year
        
        # studio
        studio = movie.xpath('.//a[contains(@href,"makers")]')[0].text_content()
        metadata.studio = studio
        Log(studio)
        
        # genres
        genres = movie.xpath('.//a[contains(@href,"tags")]')
        if len(genres) > 0:
            metadata.genres.clear()
            for genreLine in genres:
                metadata.genres.add(genreLine.text_content().strip())

        # directors
        directors = movie.xpath('.//a[contains(@href,"directors")]')
        if len(directors) > 0:
            metadata.directors.clear()
            for person in directors:
                director = metadata.directors.new()
                director.name = person.text_content()
    except Exception as e:
        Log(e)
