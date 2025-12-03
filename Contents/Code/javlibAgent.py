# -*- coding: utf-8 -*-
#import urllib
import urllib2
import re
import ssl
import json
from datetime import datetime
from lxml import html

SEARCH_URL = 'https://www.javlibrary.com/ja/vl_searchbyid.php?keyword=%s'
curID = "javlib"
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

def videoAttrs(ele):
    id = ele.split("%2F")[-1].rsplit("%2E",1)[0].replace("-C","")
    #if ele.split("-C")[1] is not None:
    #    subbed = True
    #return [id, subbed]

def search(query, results, media, lang):
    try:
        Log('Search Query: %s' % str(SEARCH_URL % query))
        res = getElementFromUrl(SEARCH_URL % query)
        video_id_tds = res.xpath('//div[@id="video_id"]//td')
        if len(video_id_tds) > 1:
            movieurl = 'https://www.javlibrary.com' + res.xpath('//div[@id="video_title"]//a')[0].get('href')
            Log(movieurl)
            movieid = video_id_tds[1].text_content()
            score = 100
            title = res.xpath('//div[@id="video_title"]//a')[0].text_content()
            movieurl = str(movieurl).replace('/','_x_').replace('=','_d_').replace('?','_q_')
            results.Append(MetadataSearchResult(id = curID + "|" + str(movieurl) + "|" + str(media.filename).split('%2F')[-1],
                                                name=str("javlib " + title),
                                                score=score,lang=lang
                                                ))
                
        else: 
            for mmm in res.xpath('//div[@class="video"]'):
                movieurl = 'https://www.javlibrary.com/ja/' + str(mmm.xpath('./a')[0].get('href')).replace('./','')
                movieid = mmm.xpath('./a/div[@class="id"]/text()')[0]
                score = 100-3*Util.LevenshteinDistance(query,movieid)
                title = str(mmm.xpath('./a/@title')[0])                
                movieurl = str(movieurl).replace('/','_x_').replace('=','_d_').replace('?','_q_')
                results.Append(MetadataSearchResult(id = curID + "|" + str(movieurl) + "|" + str(media.filename),
                                                    name=str("javlib " + title),
                                                    score=score,lang=lang
                                                    ))
            
        results.Sort('score', descending=True)
        #for line in results:
         #   Log(line)
    except Exception as e: Log(e)

def update(metadata, media, lang):
    #Log(metadata.id)
    if curID != str(metadata.id).split("|")[0]:
        Log("ID doesn't match")
        return
    metadata.id = metadata.id.replace('_x_','/').replace('_d_','=').replace('_q_','?')
    Log("Begin UPDATE")
    url = str(metadata.id).split("|")[1]
    Log('Update Query: %s' % url)
    try:
        tree = getElementFromUrl(url)
        if tree is None:
            Log("Update: no HTML tree returned for URL: %s" % url)
            return
        
        movie = tree.xpath('//body')
        if not movie:
            titles = tree.xpath('//title/text()')
            title = titles[0] if titles else 'NO_TITLE'
            try:
                snippet = html.tostring(tree)[:1000]
            except Exception:
                snippet = 'unable to serialize tree'
            Log("Update: body tag missing. Title: %s. Snippet: %s" % (title, snippet))
            return
        
        movie = movie[0]
        
        #ID
        video_id_nodes = movie.xpath('//div[@id="video_id"]//td')
        if len(video_id_nodes) > 1:
            movieid = video_id_nodes[1].text_content()
            Log(movieid)
        else:
            Log("Update: video_id not found")

        #Title
        title_nodes = movie.xpath('//div[@id="video_title"]//a')
        if title_nodes:
            metadata.title = title_nodes[0].text_content()
        else:
            Log("Update: title not found")
                
        #COVER
        jacket_nodes = movie.xpath('//img[@id="video_jacket_img"]')
        if jacket_nodes:
            try:
                imageurl = str(jacket_nodes[0].get('src'))
                if re.search("^//",imageurl):
                    imageurl = "http:" + imageurl
                thumbUrl = imgProxy + imageurl
                try:
                    thumb = request(thumbUrl)
                    posterUrl = imgProxy + imageurl
                    metadata.posters[posterUrl] = Proxy.Preview(thumb)
                except Exception as fetchErr:
                    Log("Failed to fetch poster %s: %s" % (thumbUrl, str(fetchErr)))
            except Exception as e:
                Log("Error processing image: %s" % str(e))
        else:
            Log("Update: video_jacket_img not found")
        
        #Actor
        try:
            for actor in movie.xpath('//div[@id="video_cast"]/table//a/text()'):
                Log(actor)
                role = metadata.roles.new()
                role.name = actor
                metadata.collections.add(role.name)
        except Exception as e:
            Log("Error processing actors: %s" % str(e))

        #Date
        date_nodes = movie.xpath('//div[@id="video_date"]//td/text()')
        if len(date_nodes) > 1:
            try:
                moviedate = date_nodes[1]
                metadata.originally_available_at = datetime.strptime(moviedate, '%Y-%m-%d')
                metadata.year = metadata.originally_available_at.year
                Log('Found Date: %s' % metadata.originally_available_at)
            except Exception as e:
                Log("Failed to parse date '%s': %s" % (moviedate, str(e)))
        else:
            Log("Update: date not found")

        #Studio
        studio_nodes = movie.xpath('//div[@id="video_maker"]//a/text()')
        if studio_nodes:
            studio = studio_nodes[0]
            Log('Studio Found: %s' % studio)
            metadata.studio = studio
        else:
            Log("Update: studio not found")

        #Director
        director_nodes = movie.xpath('//div[@id="video_director"]//td//text()')
        if len(director_nodes) > 1:
            director = director_nodes[1]
            if director:
                metadata.directors.clear()
                new_director = metadata.directors.new()
                new_director.name = director
                Log('Director Found: %s' % new_director.name)
        else:
            Log("Update: director not found")

        #Tags
        tags = movie.xpath('//div[@id="video_genres"]//a/text()')
        Log(tags)
        if len(tags) > 1 :
            metadata.genres.clear()
            for tag in tags:
                metadata.genres.add(tag)
    except Exception as e: 
        Log("Update exception: %s" % str(e))
