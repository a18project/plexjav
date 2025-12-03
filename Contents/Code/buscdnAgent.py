import urllib2
import ssl
import re
from datetime import datetime
from lxml import html
#from PIL import Image

BASE_URL = 'https://www.buscdn.me'
SEARCH_URL = BASE_URL + '/ja/search/%s'
curID = "BusCDN"
imgProxy = 'http://192.168.1.11:8282/insecure/rs:fill:380:536/g:ea/plain/'


def getElementFromUrl(url):
    return html.fromstring(request(url))


def request(url):
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent, }
    Log('Requesting: %s' % url)
    request = urllib2.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib2.urlopen(request, context=ctx).read()


def elementToString(ele):
    html.tostring(ele, encoding='unicode')


def search(query, results, media, lang):
    try:
        url = str(SEARCH_URL % query)
        for movie in getElementFromUrl(url).xpath('//a[contains(@class,"movie-box")]'):
            movieid = movie.get("href").replace('/', "_")
            score=99-3*Util.LevenshteinDistance(query,movieid.split('ja_')[1])
            results.Append(MetadataSearchResult(id=curID + "|" + str(movieid) + "|" + str(media.filename),
                                                name=str(movieid.split('ja_')[1]+" - %s" % curID), score=score, lang=lang))
        results.Sort('score', descending=True)
    except Exception as e:
        Log(e)


def update(metadata, media, lang):
    if curID != str(metadata.id).split("|")[0]:
        return

    query = str(metadata.id).split("|")[1].replace('_', '/', 4)
    if re.search('\d{4}-\d\d-\d\d$', query):
        query = query.replace('/ja', '')
    Log('Update Query: %s' % str(query))
    try:
        movie = getElementFromUrl(query).xpath('//div[@class="container"]')[0]

        # title
        if movie.xpath('.//h3'):
            metadata.title = movie.xpath('.//h3')[0].text_content().strip()

        # poster
        image = movie.xpath('.//a[contains(@class,"bigImage")]')[0]
        thumbUrl = imgProxy + BASE_URL + image.get('href')
        thumb = request(thumbUrl)
        posterUrl = imgProxy + BASE_URL + image.get('href')
        metadata.posters[posterUrl] = Proxy.Preview(thumb)

        # actors
        metadata.roles.clear()
        for actor in movie.xpath('.//a[@class="avatar-box"]'):
            img = actor.xpath('.//img')[0]
            role = metadata.roles.new()
            role.name = img.get("title")
            if 'nowprinting' not in img.get("src"):
                role.photo = BASE_URL + img.get("src")
            Log("Actor Pic: %s" % role.photo)
            metadata.collections.add(role.name)
            Log('Actor: %s' % role.name)

        for ele in movie.xpath('.//p'):
            ele = ele.text_content().strip()
            # release date & year
            if ele.find('発売日') != -1 or ele.find('發行日期') != -1:
                moviedate = ele.replace('発売日: ', '').replace('Release Date: ', '').replace('發行日期: ', '')
                metadata.originally_available_at = datetime.strptime(
                moviedate, '%Y-%m-%d')
                metadata.year = metadata.originally_available_at.year
                Log('Found Date: %s' % metadata.originally_available_at)
            # studio
            if ele.find('メーカー') != -1 or ele.find('製作商') != -1:
                studio = ele.replace('メーカー: ', '').replace('製作商: ', '')
                Log('Studio Found: %s' % studio)
                metadata.studio = studio
            elif ele.find('レーベル') != -1 or ele.find('發行商') != -1:
                studio = ele.replace('レーベル: ', '').replace('發行商: ', '')
                Log('Studio Found: %s' % studio)
                metadata.studio = studio
            # Director
            if ele.find('監督') != -1 or ele.find('導演') != -1 :
                metadata.directors.clear()
                director = metadata.directors.new()
                director.name = ele.replace('監督: ','').replace('導演: ','')
                Log('Director Found: %s' % director.name)

        # genres
        genres = movie.xpath('.//span[@class="genre"]')
        if len(genres) > 0:
            metadata.genres.clear()
            for genreLine in genres:
                metadata.genres.add(genreLine.text_content().strip())
        Log("ok %s" % genres)

    except Exception as e:
        Log(e)
