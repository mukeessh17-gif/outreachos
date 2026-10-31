# Day 4: HTTP and REST APIs
# OutreachOS - AI sales outreach tool
# Run this file from inside the week1/ folder.

# ==================================================================
# 1. Plain-English explanation
# ==================================================================
# HTTP is the language browsers and programs use to ask for and send
# information over the internet. It works like a request and a reply.
# GET means "give me some data" - for example, asking for a user's profile.
# POST means "here is some data, please save or process it" - for example,
# sending a new lead to a server.
# A status code is a number the server sends back to say what happened:
#   200 means OK, the request worked.
#   404 means Not Found, the page or resource does not exist.
#   500 means Internal Server Error, something went wrong on the server.
# JSON in an API response looks like a Python list or dictionary, but as
# text. Example: {"name": "Jane", "city": "Coimbatore", "employees": 12}

# ==================================================================
# 2. Install requests (run this in your terminal, not in Python):
#    pip install requests
#    Then add "requests" to requirements.txt
# ==================================================================
import requests

# ==================================================================
# 3. Call a free public API that needs no key
# ==================================================================
# jsonplaceholder.typicode.com is a free test API. No API key needed.
url = "https://jsonplaceholder.typicode.com/users"

try:
    # timeout=10 means stop waiting after 10 seconds if nothing answers.
    response = requests.get(url, timeout=10)

    # Print the status code to see if the request worked.
    print("Status code:", response.status_code)

    # If the status code is 200, read and print 3 fields from the JSON.
    if response.status_code == 200:
        # .json() turns the response text into Python data (list of dicts).
        users = response.json()
        # Print the first 3 users, showing name, email, and website.
        for user in users[:3]:
            print("Name:", user["name"])
            print("Email:", user["email"])
            print("Website:", user["website"])
            print("---")
    else:
        # Status code was not 200, so explain what we got.
        print("The API returned status code", response.status_code)

# requests.exceptions.RequestException catches network errors,
# timeouts, DNS failures, and anything else that goes wrong with the request.
except requests.exceptions.RequestException as error:
    print("Sorry, something went wrong calling the API:", error)

# ==================================================================
# 4. Show what a 404 looks like
# ==================================================================
# Request a URL that does not exist so you can see a 404 response.
bad_url = "https://jsonplaceholder.typicode.com/nope-not-real"

try:
    response_404 = requests.get(bad_url, timeout=10)
    print("404 demo status code:", response_404.status_code)
    # A 404 means the server got the request but the page does not exist.
except requests.exceptions.RequestException as error:
    print("404 demo error:", error)

# ==================================================================
# 5. TODO: fetch_users()
# ==================================================================
# TODO: Write fetch_users() here.
# It should:
#   - call requests.get() on the same users API
#   - return the list of dictionaries from response.json()
#   - use your save_leads(path, leads) from Day 3 to save them
#   - print how many users were saved
# def fetch_users():
#     ...

print("Day 4 exercises complete.")