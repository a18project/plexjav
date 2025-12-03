import requests
# You would need to define Log or use print
# def Log(message):
#     print message

def tests():
    url = "http://192.168.1.11:8191/v1"
    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": "request.get",
        "url": "http://www.javlibrary.com/",
        "maxTimeout": 20000
    }
    
    try:
        # 1. Attempt to make the POST request
        # Setting a separate, short timeout for the connection itself
        response = requests.post(url, headers=headers, json=data, timeout=60) 
        
        # 2. Check for bad HTTP status codes (e.g., 4xx or 5xx)
        # This will raise an HTTPError for non-200 status codes
        response.raise_for_status() 

        # 3. Log the successful response text
        Log("Successfully received response:")
        Log(response.text)

    # --- Specific Exception Handlers ---
    
    except requests.exceptions.Timeout, e:
        # Catches a timeout error (e.g., if the server is too slow)
        Log("ERROR: Request timed out. Check server and network.")
        Log(e)

    except requests.exceptions.ConnectionError, e:
        # Catches network-related errors (e.g., refused connection, DNS failure)
        Log("ERROR: Connection failed. Is the server running at %s?" % url)
        Log(e)

    except requests.exceptions.HTTPError, e:
        # Catches bad HTTP status codes (e.g., 404, 500)
        Log("ERROR: HTTP request failed with status code %s" % response.status_code)
        Log(e)
        Log("Server response text:")
        Log(response.text)

    except requests.exceptions.RequestException, e:
        # Catches any other requests-related exception not caught above
        Log("ERROR: An unexpected error occurred during the request.")
        Log(e)
        
    except Exception, e:
        # Catches any other non-requests error (e.g., a bug in Log function)
        Log("ERROR: A non-request related error occurred.")
        Log(e)