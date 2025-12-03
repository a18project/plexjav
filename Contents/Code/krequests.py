#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
krequests - A Python 2.7 module for bypassing Cloudflare protection
with automatic FlareSolverr integration.
"""

import urllib2
import json


class KRequests:
    """
    A requests-like module for bypassing Cloudflare protection using FlareSolverr.
    """
    
    def __init__(self, flaresolverr_url="http://192.168.1.11:8191/v1", timeout=10000, default_session=None):
        self.flaresolverr_url = flaresolverr_url
        self.timeout = timeout
        self.default_session = default_session
    
    def detect_cloudflare(self, url):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', self.getUserAgent())
            
            response = urllib2.urlopen(request)
            headers = dict(response.info())
            content = response.read()
            status_code = response.getcode()
            
            return self.analyzeCloudflare(headers, content, status_code)
            
        except urllib2.HTTPError as e:
            headers = dict(e.info())
            return self.analyzeCloudflare(headers, "", e.code, True)
            
        except Exception as e:
            return {
                'protected': False,
                'captcha_active': False,
                'reason': 'Detection error: ' + str(e),
                'headers': {},
                'status_code': None
            }
    
    def get(self, url, force_flaresolverr=False, session=None):
        return self.fetchPage(url, "GET", force_flaresolverr, session)
    
    def post(self, url, data=None, force_flaresolverr=False, session=None):
        if not force_flaresolverr:
            cf_detection = self.detect_cloudflare(url)
            force_flaresolverr = cf_detection['protected'] or cf_detection['captcha_active']
        
        if force_flaresolverr:
            return self.flaresolverrPost(url, data, session)
        else:
            return self.directPost(url, data)
    
    def create_session(self, session_name=None):
        name = session_name or self.default_session
        if not name:
            return {"success": False, "error": "No session name provided"}
        
        data = {"cmd": "sessions.create", "session": name}
        return self.sendFlareSolverrCommand(data)
    
    def destroy_session(self, session_name=None):
        name = session_name or self.default_session
        if not name:
            return {"success": False, "error": "No session name provided"}
        
        data = {"cmd": "sessions.destroy", "session": name}
        return self.sendFlareSolverrCommand(data)
    
    def list_sessions(self):
        data = {"cmd": "sessions.list"}
        return self.sendFlareSolverrCommand(data)
    
    def getUserAgent(self):
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def analyzeCloudflare(self, headers, content, status_code, is_error=False):
        server_header = headers.get('server', '').lower()
        has_cf_ray = 'cf-ray' in headers
        has_cf_challenge = 'cf-challenge' in headers
        
        captcha_indicators = [
            'cf-browser-verification',
            'challenge-form',
            'data-translate="why_captcha_detail"',
            'turnstile',
            'Checking your browser',
            'Please complete this security check'
        ]
        
        has_captcha = False
        for indicator in captcha_indicators:
            if indicator in content:
                has_captcha = True
                break
        
        is_cloudflare = 'cloudflare' in server_header or has_cf_ray
        
        result = {
            'protected': is_cloudflare,
            'captcha_active': has_cf_challenge or has_captcha,
            'reason': '',
            'headers': headers,
            'status_code': status_code
        }
        
        if has_cf_challenge:
            result['reason'] = 'Cloudflare challenge in headers'
        elif has_captcha:
            result['reason'] = 'Cloudflare CAPTCHA content detected'
        elif is_cloudflare:
            result['reason'] = 'Cloudflare protection detected'
        else:
            result['reason'] = 'No Cloudflare protection'
            
        return result
    
    def fetchPage(self, url, method, force_flaresolverr, session):
        if not force_flaresolverr:
            cf_detection = self.detect_cloudflare(url)
            use_flaresolverr = cf_detection['protected'] or cf_detection['captcha_active']
        else:
            use_flaresolverr = True
        
        if use_flaresolverr:
            return self.flaresolverrRequest(url, method, session)
        else:
            return self.directRequest(url, method)
    
    def flaresolverrRequest(self, url, method="GET", session=None):
        cmd = "request.get" if method.upper() == "GET" else "request.post"
        
        data = {
            "cmd": cmd,
            "url": url,
            "maxTimeout": self.timeout
        }
        
        sess = session or self.default_session
        if sess:
            data["session"] = sess
        
        result = self.sendFlareSolverrCommand(data)
        
        if result.get("success"):
            solution = result.get("solution", {})
            # Extract the response content properly
            response_content = solution.get("response", "")
            # If response is a string, use it directly
            if isinstance(response_content, (str, unicode)):
                content = response_content
            else:
                # If it's some other type, convert to string
                content = str(response_content)
                
            return {
                'success': True,
                'content': content,
                'status_code': solution.get("status", 200),
                'headers': solution.get("headers", {}),
                'used_flaresolverr': True,
                'cloudflare_detected': True,
                'error': None
            }
        else:
            return {
                'success': False,
                'content': None,
                'status_code': result.get("status_code"),
                'headers': {},
                'used_flaresolverr': True,
                'cloudflare_detected': True,
                'error': result.get("error", "Unknown FlareSolverr error")
            }
    
    def flaresolverrPost(self, url, data, session):
        post_data = {
            "cmd": "request.post",
            "url": url,
            "maxTimeout": self.timeout
        }
        
        if data:
            post_data["postData"] = json.dumps(data)
        
        sess = session or self.default_session
        if sess:
            post_data["session"] = sess
        
        result = self.sendFlareSolverrCommand(post_data)
        
        if result.get("success"):
            solution = result.get("solution", {})
            # Extract the response content properly
            response_content = solution.get("response", "")
            # If response is a string, use it directly
            if isinstance(response_content, (str, unicode)):
                content = response_content
            else:
                # If it's some other type, convert to string
                content = str(response_content)
                
            return {
                'success': True,
                'content': content,
                'status_code': solution.get("status", 200),
                'headers': solution.get("headers", {}),
                'used_flaresolverr': True,
                'cloudflare_detected': True,
                'error': None
            }
        else:
            return {
                'success': False,
                'content': None,
                'status_code': result.get("status_code"),
                'headers': {},
                'used_flaresolverr': True,
                'cloudflare_detected': True,
                'error': result.get("error", "Unknown FlareSolverr error")
            }
    
    def directRequest(self, url, method):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', self.getUserAgent())
            
            if method.upper() == "GET":
                response = urllib2.urlopen(request)
            else:
                response = urllib2.urlopen(request, data="")
            
            content = response.read()
            headers = dict(response.info())
            
            return {
                'success': True,
                'content': content,
                'status_code': response.getcode(),
                'headers': headers,
                'used_flaresolverr': False,
                'cloudflare_detected': False,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'content': None,
                'status_code': None,
                'headers': {},
                'used_flaresolverr': False,
                'cloudflare_detected': False,
                'error': "Direct request failed: " + str(e)
            }
    
    def directPost(self, url, data):
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', self.getUserAgent())
            request.add_header('Content-Type', 'application/json')
            
            json_data = json.dumps(data) if data else ""
            response = urllib2.urlopen(request, json_data)
            content = response.read()
            headers = dict(response.info())
            
            return {
                'success': True,
                'content': content,
                'status_code': response.getcode(),
                'headers': headers,
                'used_flaresolverr': False,
                'cloudflare_detected': False,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'content': None,
                'status_code': None,
                'headers': {},
                'used_flaresolverr': False,
                'cloudflare_detected': False,
                'error': "Direct POST failed: " + str(e)
            }
    
    def sendFlareSolverrCommand(self, data):
        json_data = json.dumps(data)
        headers = {"Content-Type": "application/json"}
        
        try:
            req = urllib2.Request(self.flaresolverr_url, json_data, headers)
            response = urllib2.urlopen(req, timeout=self.timeout / 1000.0)
            response_data = response.read()  # This returns a string
            # Parse the JSON response
            return json.loads(response_data)
        except urllib2.HTTPError as e:
            error_content = e.read() if hasattr(e, 'read') else str(e)
            return {
                "success": False,
                "error": "HTTP Error: " + str(e.code) + " - " + str(e.reason),
                "status_code": e.code
            }
        except urllib2.URLError as e:
            return {
                "success": False,
                "error": "Connection Error: " + str(e.reason),
                "status_code": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": "FlareSolverr Error: " + str(e),
                "status_code": None
            }


# Convenience functions
def get(url, force_flaresolverr=False, **kwargs):
    kr = KRequests(**kwargs)
    return kr.get(url, force_flaresolverr)


def post(url, data=None, force_flaresolverr=False, **kwargs):
    kr = KRequests(**kwargs)
    return kr.post(url, data, force_flaresolverr)


def detect_cloudflare(url):
    kr = KRequests()
    return kr.detect_cloudflare(url)


# Simple test function that doesn't rely on external services
def test():
    print("Testing krequests module initialization...")
    
    # Test basic initialization
    kr = KRequests()
    print("KRequests initialized successfully")
    
    # Test Cloudflare detection with a simple site
    result = kr.detect_cloudflare("http://www.example.com")
    print("Cloudflare detection test completed")
    print("Protected: " + str(result['protected']))
    print("Reason: " + result['reason'])
    
    print("Basic module test passed!")


if __name__ == "__main__":
    test()