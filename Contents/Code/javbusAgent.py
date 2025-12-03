import urllib2
import ssl
import re
import hashlib
import os
from datetime import datetime
from lxml import html

BASE_URL = 'https://www.javbus.com'
SEARCH_URL = BASE_URL + '/ja/search/%s'
curID = "Javbus"
imgProxy = 'http://192.168.1.11:8282/insecure/rs:fill:380:536/g:ea/plain/'

cookies = {
    'existmag': 'mag',
    'dv': '1'
}


def getElementFromUrl(url):
    content = request(url)
    if not content:
        Log('getElementFromUrl: no content for %s' % url)
        return None
    return html.fromstring(content)


def request(url, referer=None):
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent}
    if referer:
        headers['Referer'] = referer
    headers['Cookie'] = '; '.join(['%s=%s' % (k, v) for k, v in cookies.items()])
    Log('Requesting: %s (referer=%s)' % (url, referer))
    try:
        req = urllib2.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib2.urlopen(req, context=ctx).read()
    except Exception as e:
        Log('Request error for %s: %s' % (url, str(e)))
        return None

# Helper: save bytes to /transcode and return path (or None)
def save_local_image(bytes_data, prefix='javbus'):
    if not bytes_data:
        return None
    image_dir = '/transcode'
    try:
        if not os.path.exists(image_dir):
            try:
                os.makedirs(image_dir)
            except Exception:
                pass
        fname = '%s_%s.jpg' % (prefix, hashlib.md5(bytes_data).hexdigest())
        file_path = os.path.join(image_dir, fname)
        fd = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, bytes_data)
        finally:
            os.close(fd)
        return file_path
    except Exception as e:
        Log('save_local_image failed: %s' % str(e))
        return None

# Helper: clear existing posters/art and register bytes
def register_poster_bytes(metadata, bytes_data):
    """Clear existing posters/art on the provided metadata object and register bytes_data."""
    if not bytes_data:
        return False
    try:
        try:
            metadata.posters.clear()
            try:
                metadata.art.clear()
            except Exception:
                pass
        except Exception:
            pass
        key = 'javbus:' + hashlib.md5(bytes_data).hexdigest()
        metadata.posters[key] = Proxy.Media(bytes_data)
        Log('Registered poster key=%s len=%d' % (key, len(bytes_data)))
        return True
    except Exception as e:
        Log('register_poster_bytes error: %s' % str(e))
        return False


def search(query, results, media, lang):
    try:
        url = str(SEARCH_URL % query)
        for movie in getElementFromUrl(url).xpath('//a[contains(@class,"movie-box")]'):
            movieid = movie.get("href").replace('/', "_")
            score=98-3*Util.LevenshteinDistance(query,movieid.split('ja_')[1])
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

    # add page referer once for reuse
    pageUrl = query if query.startswith('http') else BASE_URL + query

    try:
        movie = getElementFromUrl(query).xpath('//div[@class="container"]')[0]

        # title
        if movie.xpath('.//h3'):
            metadata.title = movie.xpath('.//h3')[0].text_content().strip()

        # actors
        metadata.roles.clear()
        for actor in movie.xpath('.//a[@class="avatar-box"]'):
            img = actor.xpath('.//img')[0]
            role = metadata.roles.new()
            role.name = img.get("title")

            # fetch actor image bytes with Referer and register as a role photo using Proxy.Preview
            try:
                actor_url = BASE_URL + img.get("src")
                actor_bytes = request(actor_url, referer=pageUrl)
                if actor_bytes:
                    try:
                        # Assign a preview/media object directly to the role photo instead.
                        role.photo = Proxy.Media(actor_bytes)
                        Log("Actor Pic fetched and assigned to role.photo: %s (len=%d)" % (actor_url, len(actor_bytes)))
                    except Exception as e:
                        # Fallback to using the URL if Proxy.Media assignment fails
                        role.photo = actor_url
                        Log("Failed to assign Proxy.Media for actor photo, using URL: %s (%s)" % (actor_url, str(e)))
                else:
                    role.photo = actor_url
                    Log("Actor Pic fetch returned no bytes, using URL: %s" % actor_url)
            except Exception as e:
                role.photo = BASE_URL + img.get("src")
                Log("Actor Pic fetch error: %s" % str(e))

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
    
    # poster
    try:
        image = movie.xpath('.//a[contains(@class,"bigImage")]')[0]
        imageUrl = BASE_URL + image.get('href')
        # fetch with referer
        thumb = request(imageUrl, referer=pageUrl)
        Log('Fetched image bytes: %s (len=%d)' % (imageUrl, len(thumb) if thumb else 0))
        if not thumb:
            Log('No image bytes fetched; skipping poster')
        else:
            # save to /transcode and ask imgProxy to process local file if available
            file_path = save_local_image(thumb, prefix='javbus')
            processed = None
            if file_path:
                try:
                    local_file_url = 'local:///plex/' + os.path.basename(file_path)
                    proxy_url = imgProxy + local_file_url
                    processed = request(proxy_url)
                    Log('imgProxy processed local file: %s (len=%d)' % (proxy_url, len(processed) if processed else 0))
                except Exception as e:
                    Log('imgProxy processing failed: %s' % str(e))

            # register processed (if available) else original bytes
            if processed:
                register_poster_bytes(metadata, processed)
            else:
                register_poster_bytes(metadata, thumb)
    except Exception as e:
        Log('Poster handling error: %s' % str(e))

