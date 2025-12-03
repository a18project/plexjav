#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
JAV Trailer Scraper Module
A module to scrape JAV trailer information from javtrailers.com
"""

import urllib2
import json
from lxml import html
import sys
import time


class JAVTrailerScraper:
    """
    A scraper for JAV trailer information from javtrailers.com
    """
    
    def __init__(self, flaresolverrurl="http://localhost:8191/v1", timeout=60):
        """
        Initialize the scraper
        
        Args:
            flaresolverrurl (str): FlareSolverr server URL
            timeout (int): Request timeout in seconds
        """
        self.flaresolverrurl = flaresolverrurl
        self.timeout = timeout
        self.lastrequesttime = 0
        self.requestdelay = 2  # Delay between requests to be polite
        
    def makerequest(self, url, data=None, headers=None, method="GET"):
        """
        Make HTTP request using urllib2
        
        Args:
            url (str): Target URL
            data (str): POST data
            headers (dict): Request headers
            method (str): HTTP method
            
        Returns:
            str: Response content or None if error
        """
        # Respect rate limiting
        currenttime = time.time()
        if currenttime - self.lastrequesttime < self.requestdelay:
            time.sleep(self.requestdelay - (currenttime - self.lastrequesttime))
        
        try:
            if data and method.upper() == "POST":
                req = urllib2.Request(url, data, headers or {})
            else:
                req = urllib2.Request(url, headers=headers or {})
            
            response = urllib2.urlopen(req, timeout=self.timeout)
            self.lastrequesttime = time.time()
            return response.read()
            
        except urllib2.URLError as e:
            raise Exception("URL Error: %s" % str(e))
        except urllib2.HTTPError as e:
            raise Exception("HTTP Error %s: %s" % (e.code, e.reason))
        except Exception as e:
            raise Exception("Request Error: %s" % str(e))
    
    def getpageviaflaresolverr(self, url):
        """
        Get page content using FlareSolverr to bypass protection
        
        Args:
            url (str): Target URL to scrape
            
        Returns:
            str: Page content or None if error
        """
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
            "cookies": [
                {"name": "domain_switch", "value": "ja", "domain": ".javtrailers.com"}
            ]
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            responsedata = self.makerequest(
                self.flaresolverrurl,
                data=json.dumps(payload),
                headers=headers,
                method="POST"
            )
            
            if responsedata:
                result = json.loads(responsedata)
                if result.get('status') == 'ok':
                    return result['solution']['response']
                else:
                    raise Exception("FlareSolverr error: %s" % result.get('message', 'Unknown error'))
            
        except Exception as e:
            raise Exception("FlareSolverr request failed: %s" % str(e))
    
    def getpagedirect(self, url):
        """
        Get page content directly without FlareSolverr
        
        Args:
            url (str): Target URL to scrape
            
        Returns:
            str: Page content or None if error
        """
        headers = {
            'UserAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'AcceptLanguage': 'ja,enUS;q=0.7,en;q=0.3',
            'AcceptEncoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'UpgradeInsecureRequests': '1',
            'Referer': 'https://javtrailers.com/',
        }
        
        return self.makerequest(url, headers=headers)
    
    def extractinfo(self, pagecontent, code=None):
        """
        Extract JAV information from page content using XPath
        
        Args:
            pagecontent (str): HTML page content
            code (str): Expected product code for validation
            
        Returns:
            dict: Extracted information
        """
        if not pagecontent:
            raise ValueError("No page content provided")
        
        tree = html.fromstring(pagecontent)
        info = {'success': False}
        
        try:
            # Title
            titlexpaths = [
                '//h1[@class="entry-title"]/text()',
                '//h1[@class="single-title"]/text()',
                '//title/text()'
            ]
            info['title'] = self.extractfirst(tree, titlexpaths, 'N/A')
            
            # Video URL (trailer)
            videoxpaths = [
                '//video/source/@src',
                '//div[contains(@class, "video-container")]//iframe/@src',
                '//iframe[contains(@src, "youtube")]/@src'
            ]
            info['videourl'] = self.extractfirst(tree, videoxpaths, 'N/A')
            
            # Cover image
            coverxpaths = [
                '//div[@class="entry-content"]//img/@src',
                '//div[contains(@class, "cover-image")]//img/@src',
                '//img[contains(@class, "cover")]/@src'
            ]
            info['coverimage'] = self.extractfirst(tree, coverxpaths, 'N/A')
            
            # Actresses
            actressxpaths = [
                '//a[contains(@href, "actress")]/text()',
                '//span[contains(@class, "actress")]/a/text()',
                '//div[contains(@class, "actress-list")]//a/text()'
            ]
            info['actresses'] = self.extractlist(tree, actressxpaths)
            
            # Release date
            datexpaths = [
                '//span[contains(text(), "配信開始日")]/following-sibling::text()',
                '//span[contains(text(), "Release Date")]/following-sibling::text()',
                '//li[contains(text(), "配信開始日")]/text()'
            ]
            info['releasedate'] = self.extractfirst(tree, datexpaths, 'N/A')
            
            # Code
            codexpaths = [
                '//span[contains(text(), "品番")]/following-sibling::text()',
                '//span[contains(text(), "Code")]/following-sibling::text()',
                '//li[contains(text(), "品番")]/text()'
            ]
            extractedcode = self.extractfirst(tree, codexpaths, 'N/A')
            info['code'] = extractedcode
            
            # Validate code if provided
            if code and extractedcode != 'N/A' and code.upper() not in extractedcode.upper():
                print "Warning: Extracted code '%s' doesn't match expected code '%s'" % (extractedcode, code)
            
            # Studio/maker
            studioxpaths = [
                '//a[contains(@href, "maker")]/text()',
                '//span[contains(@class, "studio")]/a/text()',
                '//li[contains(text(), "メーカー")]/a/text()'
            ]
            info['studio'] = self.extractfirst(tree, studioxpaths, 'N/A')
            
            # Tags/categories
            tagsxpaths = [
                '//a[contains(@href, "genre")]/text()',
                '//span[contains(@class, "tags")]//a/text()',
                '//div[contains(@class, "categories")]//a/text()'
            ]
            info['tags'] = self.extractlist(tree, tagsxpaths)
            
            # Duration
            durationxpaths = [
                '//span[contains(text(), "収録時間")]/following-sibling::text()',
                '//span[contains(text(), "Duration")]/following-sibling::text()',
                '//li[contains(text(), "収録時間")]/text()'
            ]
            info['duration'] = self.extractfirst(tree, durationxpaths, 'N/A')
            
            # Description
            descxpaths = [
                '//div[@class="entry-content"]//p/text()',
                '//div[contains(@class, "description")]//p/text()',
                '//meta[@name="description"]/@content'
            ]
            info['description'] = self.extractdescription(tree, descxpaths)
            
            # Page URL (for reference)
            info['pageurl'] = 'N/A'
            
            info['success'] = True
            
        except Exception as e:
            info['error'] = "Extraction error: %s" % str(e)
            info['success'] = False
        
        return info
    
    def extractfirst(self, tree, xpaths, default='N/A'):
        """Extract first matching value from multiple XPaths"""
        for xpath in xpaths:
            results = tree.xpath(xpath)
            if results:
                value = results[0].strip()
                if value:
                    return value
        return default
    
    def extractlist(self, tree, xpaths):
        """Extract list of values from multiple XPaths"""
        for xpath in xpaths:
            results = tree.xpath(xpath)
            if results:
                return [item.strip() for item in results if item.strip()]
        return []
    
    def extractdescription(self, tree, xpaths):
        """Extract and clean description text"""
        for xpath in xpaths:
            results = tree.xpath(xpath)
            if results:
                if xpath == '//meta[@name="description"]/@content':
                    return results[0].strip()
                else:
                    text = ' '.join([text.strip() for text in results if text.strip()])
                    if text:
                        return text
        return 'N/A'
    
    def scrape(self, url, useflaresolverr=True, validatecode=True):
        """
        Main method to scrape JAV information from a URL
        
        Args:
            url (str): URL to scrape
            useflaresolverr (bool): Whether to use FlareSolverr
            validatecode (bool): Whether to validate product code from URL
            
        Returns:
            dict: Scraped information
        """
        # Extract code from URL for validation
        code = None
        if validatecode:
            import re
            match = re.search(r'/([a-zA-Z]+-\d+)', url)
            if match:
                code = match.group(1).upper()
        
        print "Scraping: %s" % url
        if code:
            print "Expected code: %s" % code
        
        # Get page content
        pagecontent = None
        methodused = ""
        
        if useflaresolverr:
            try:
                pagecontent = self.getpageviaflaresolverr(url)
                methodused = "FlareSolverr"
            except Exception as e:
                print "FlareSolverr failed: %s" % str(e)
        
        if not pagecontent:
            try:
                pagecontent = self.getpagedirect(url)
                methodused = "Direct"
            except Exception as e:
                print "Direct method failed: %s" % str(e)
        
        if not pagecontent:
            return {
                'success': False,
                'error': 'Failed to retrieve page content using any method',
                'code': code or 'N/A',
                'url': url
            }
        
        print "Successfully retrieved content via %s" % methodused
        
        # Extract information
        info = self.extractinfo(pagecontent, code)
        info['scrapingmethod'] = methodused
        info['url'] = url
        
        return info

# Test function
def testscraper():
    """Test the scraper with sample URLs"""
    testurls = [
        "https://javtrailers.com/ja/cemd-749",
        "https://javtrailers.com/ja/ssis-001",
        "https://javtrailers.com/ja/mide-100"
    ]
    
    scraper = JAVTrailerScraper()
    
    for url in testurls:
        print "\n" + "="*60
        print "TESTING: %s" % url
        print "="*60
        
        try:
            result = scraper.scrape(url, useflaresolverr=True)
            
            if result['success']:
                print "✓ Successfully scraped information:"
                for key, value in result.items():
                    if key not in ['success', 'scrapingmethod']:
                        if isinstance(value, list):
                            print "  %s: %s" % (key, ', '.join(value))
                        else:
                            print "  %s: %s" % (key, value)
            else:
                print "✗ Failed to scrape: %s" % result.get('error', 'Unknown error')
                
        except Exception as e:
            print "✗ Exception during scraping: %s" % str(e)
        
        print "\n" + "-"*60

# Demo function
def demo():
    """Run a demo of the scraper"""
    print "JAV Trailer Scraper Demo"
    print "=" * 50
    
    scraper = JAVTrailerScraper()
    
    # Example URL
    url = "https://javtrailers.com/ja/cemd-749"
    
    print "Scraping: %s" % url
    print "This may take a moment..."
    
    result = scraper.scrape(url)
    
    if result['success']:
        print "\n✓ SUCCESS!"
        print "Scraping Method: %s" % result.get('scrapingmethod', 'Unknown')
        print "\nExtracted Information:"
        print "-" * 30
        
        displayfields = [
            ('Title', 'title'),
            ('Code', 'code'), 
            ('Studio', 'studio'),
            ('Release Date', 'releasedate'),
            ('Duration', 'duration'),
            ('Actresses', 'actresses'),
            ('Tags', 'tags'),
            ('Video URL', 'videourl'),
            ('Cover Image', 'coverimage'),
            ('Description', 'description')
        ]
        
        for displayname, fieldname in displayfields:
            value = result.get(fieldname, 'N/A')
            if isinstance(value, list):
                value = ', '.join(value) if value else 'N/A'
            print "%s: %s" % (displayname, value)
    else:
        print "\n✗ FAILED!"
        print "Error: %s" % result.get('error', 'Unknown error')

# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='JAV Trailer Scraper')
    parser.add_argument('url', nargs='?', help='URL to scrape')
    parser.add_argument('--test', action='store_true', help='Run tests')
    parser.add_argument('--demo', action='store_true', help='Run demo')
    parser.add_argument('--noflaresolverr', action='store_true', help='Disable FlareSolverr')
    
    args = parser.parse_args()
    
    if args.test:
        testscraper()
    elif args.demo:
        demo()
    elif args.url:
        scraper = JAVTrailerScraper()
        result = scraper.scrape(args.url, useflaresolverr=not args.noflaresolverr)
        
        if result['success']:
            print "Success: true"
            for key, value in result.items():
                if key != 'success':
                    if isinstance(value, list):
                        print "%s: %s" % (key, '|'.join(value))
                    else:
                        print "%s: %s" % (key, value)
        else:
            print "Success: false"
            print "Error: %s" % result.get('error', 'Unknown error')
            sys.exit(1)
    else:
        print "No URL provided. Use --test, --demo, or provide a URL."
        print "Examples:"
        print "  python javscraper.py --test"
        print "  python javscraper.py --demo" 
        print "  python javscraper.py https://javtrailers.com/ja/cemd-749"
        print "  python javscraper.py https://javtrailers.com/ja/ssis-001 --noflaresolverr"