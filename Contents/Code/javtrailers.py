# coding=utf-8
# JAVTrailers.com scraper for Plex Agent

import urllib2
import urllib
import ssl
import re
import json
import krequests
import javtrailersTest
from datetime import datetime
from lxml import html


BASE_URL = 'https://javtrailers.com'
SEARCH_URL = BASE_URL + '/ja/search/%s'
curID = "javtrailers"
imgProxy = 'http://192.168.1.11:8282/insecure/rs:fill:380:536/g:ea/plain/'


FLARESOLVERR_URL = 'http://192.168.1.11:8191/v1'

def request_with_flaresolverr(url, cookies=None):
    """
    Request a URL through FlareSolverr if possible.
    Be tolerant of inconsistent FlareSolverr responses: accept any returned
    solution.response content. On failure, return None so caller can fallback.
    """
    payload = {
        'cmd': 'request.get',
        'url': url,
        'maxTimeout': 30000
    }
    
    headers = {'Content-Type': 'application/json'}
    request = urllib2.Request(FLARESOLVERR_URL, data=json.dumps(payload), headers=headers)
    
    try:
        response = urllib2.urlopen(request)
        result = json.load(response)
    except Exception as e:
        # FlareSolverr unreachable or network error; signal caller to fallback.
        Log("FlareSolverr request exception: %s" % str(e))
        return None

    try:
        # Prefer explicit solution.response when available
        if isinstance(result, dict):
            # Some FlareSolverr instances may set 'success' oddly while still returning a solution
            sol = result.get('solution') or {}
            resp = sol.get('response') if isinstance(sol, dict) else None

            # Some deployments may return the HTML directly in 'response' or 'data' or 'html'
            if resp:
                return resp
            # Older/other wrappers might return under 'response' at top level
            if result.get('response'):
                return result.get('response')
            # If FlareSolverr reports success and provides a 'message' containing raw HTML (rare)
            if result.get('success') and isinstance(result.get('message'), basestring) and '<html' in result.get('message'):
                return result.get('message')
            
        # No usable response found
        Log("FlareSolverr returned no usable response: %s" % str(result))
        return None

    except Exception as e:
        Log("Error parsing FlareSolverr result: %s" % str(e))
        return None


def getElementFromUrl(url):
    """
    Get an lxml element from URL, try FlareSolverr first, fall back to direct request.
    """
    # Try FlareSolverr
    try:
        content = request_with_flaresolverr(url)
        if content:
            return html.fromstring(content)
    except Exception as e:
        Log("FlareSolverr parsing error: %s" % str(e))

    # Fallback to a simple direct request
    try:
        Log("Falling back to simple_request for URL: %s" % url)
        content = simple_request(url)
        return html.fromstring(content)
    except Exception as e:
        raise Exception('Failed to fetch and parse URL (both FlareSolverr and direct failed): %s' % str(e))


def simple_request(url):
    """
    Simple direct request without FlareSolverr (fallback).
    """
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers = {'User-Agent': user_agent}
    request = urllib2.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib2.urlopen(request, context=ctx).read()

# Add compatibility wrapper so existing code calling `request()` works
def request(url):
    """
    Compatibility wrapper named `request` used elsewhere in the file.
    Returns response bytes (str in Python2). Tries simple_request first,
    then falls back to a direct urllib2.urlopen() attempt, logging failures.
    """
    try:
        return simple_request(url)
    except Exception as e:
        Log("request() simple_request failed for %s: %s" % (url, str(e)))
        try:
            user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
            headers = {'User-Agent': user_agent}
            req = urllib2.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return urllib2.urlopen(req, context=ctx).read()
        except Exception as e2:
            Log("request() fallback failed for %s: %s" % (url, str(e2)))
            raise

def search(query, results, media, lang):    
    try:
        encoded_query = urllib.quote_plus(query)
        url = BASE_URL + '/ja/search/' + encoded_query
        Log("Search URL: " + url)
        
        # Get the HTML content and parse it
        tree = getElementFromUrl(url)
        if tree is None:
            Log("Failed to get or parse the search page")
            return
        
        # Debug: log the page title to verify parsing works
        titles = tree.xpath('//title/text()')
        if titles:
            Log("Page title: " + titles[0])
        
        # Find all movie cards
        movie_cards = tree.xpath('//div[@class="card-container"]')
        Log("Found " + str(len(movie_cards)) + " movie cards")
        
        for movie in movie_cards:
            try:
                # Extract movie path
                links = movie.xpath('.//a/@href')
                if not links:
                    continue
                moviepath = links[0].replace('/', "__")
                
                # Extract movie title
                title_elements = movie.xpath('.//p[contains(@class,"vid-title")]/text()')
                if not title_elements:
                    continue
                movietitle = title_elements[0].strip()
                
                Log("Found movie: " + movietitle)
                
                resultname = movietitle + " " + curID 
                score = 100 - 3 * Util.LevenshteinDistance(query, movietitle.split(" ")[0])
                
                results.Append(MetadataSearchResult(
                    id=curID + "|" + str(moviepath) + "|" + str(media.filename),
                    name=resultname, 
                    score=score, 
                    lang=lang
                ))
                
            except Exception as e:
                Log("Error processing movie card: " + str(e))
                continue
        
        results.Sort('score', descending=True)
        Log("Search completed, found " + str(len(results)) + " results")
        
    except Exception as e:
        Log("Error in search function: " + str(e))


def update(metadata, media, lang):
    Log(str(metadata.id))
    parts = str(metadata.id).split("|")
    if len(parts) < 2 or parts[0] != curID:
        Log("Update: unexpected metadata.id format or wrong source: %s" % str(metadata.id))
        return

    query = parts[1].replace('__', '/', 4)
    url = BASE_URL + query
    Log('Update Query: ' + url)
    try:
        tree = getElementFromUrl(url)
        if tree is None:
            Log("Update: no HTML tree returned for URL: %s" % url)
            return

        desc_nodes = tree.xpath('//div[@id="description"]')
        if not desc_nodes:
            titles = tree.xpath('//title/text()')
            title = titles[0] if titles else 'NO_TITLE'
            try:
                snippet = html.tostring(tree)[:1000]
            except Exception:
                snippet = 'unable to serialize tree'
            Log("Update: description node missing. Title: %s. Snippet: %s" % (title, snippet))
            return

        movie = desc_nodes[0]

        # title
        h1_nodes = movie.xpath('.//h1')
        if h1_nodes:
            metadata.title = h1_nodes[0].text_content()
        else:
            Log("Update: title <h1> not found for %s" % url)

        # poster
        images = movie.xpath('.//img[contains(@src,".jpg")]')
        for image in images:
            try:
                src = image.get('src') or ''
                if not src:
                    continue
                thumbUrl = imgProxy + src.replace('ps.jp','pl.jp').replace('pf_o1','pb_e')
                try:
                    thumb = request(thumbUrl)
                    metadata.posters[thumbUrl] = Proxy.Preview(thumb)
                except Exception as fetchErr:
                    Log("Failed to fetch poster %s: %s" % (thumbUrl, str(fetchErr)))
            except Exception as e:
                Log("Error processing image element: %s" % str(e))
                continue

        # actors
        actors = movie.xpath('.//a[contains(@href,"casts")]')
        if len(actors) > 0:
            metadata.roles.clear()
            for actor in actors:
                try:
                    role = metadata.roles.new()
                    role.name = actor.text_content()
                    metadata.collections.add(role.name)
                    Log("Actor: " + str(role.name))
                except Exception as e:
                    Log("Error adding actor role: %s" % str(e))

        for ele in movie.xpath('.//p[@class="mb-1"]'):
            ele = ele.text_content().strip()
            # release date & year
            if ele.find('発売日') != -1 or ele.find('發行日期') != -1:
                moviedate = ele.replace('商品発売日：', '').replace('Release Date: ', '').replace('發行日期: ', '').strip()
                try:
                    metadata.originally_available_at = datetime.strptime(moviedate, '%d %b %Y')
                    metadata.year = metadata.originally_available_at.year
                    Log("Found Date: " + str(metadata.originally_available_at))
                except Exception as e:
                    Log("Failed to parse date '%s': %s" % (moviedate, str(e)))
            # studio
            if ele.find('メーカー') != -1 or ele.find('製作商') != -1:
                studio = ele.replace('メーカー: ', '').replace('製作商: ', '')
                Log("Studio Found: " + str(studio))
                metadata.studio = studio
            elif ele.find('レーベル') != -1 or ele.find('發行商') != -1:
                studio = ele.replace('レーベル: ', '').replace('發行商: ', '')
                Log("Studio Found: " + str(studio))
                metadata.studio = studio
            # Director
            if ele.find('監督') != -1 or ele.find('導演') != -1 :
                metadata.directors.clear()
                director = metadata.directors.new()
                director.name = ele.replace('監督：','').replace('導演: ','').strip()
                Log("Director Found: " + str(director.name))

        # genres
        genres = movie.xpath('.//a[contains(@href,"categories")]')
        if len(genres) > 0:
            metadata.genres.clear()
            for genreLine in genres:
                metadata.genres.add(genreLine.text_content().strip())
        #Log("ok %s" % genres)

    except Exception as e:
        Log("Update exception: %s" % str(e))
