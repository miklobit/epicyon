__filename__ = "webfinger.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
from Crypto.PublicKey import RSA
from Crypto.Util import number
import requests
import json
import commentjson
import os
from session import getJson

def parseHandle(handle):
    if '.' not in handle:
        return None, None
    if '/@' in handle:
        domain, username = handle.replace('https://','').replace('http://','').split('/@')
    else:
        if '/users/' in handle:
            domain, username = handle.replace('https://','').replace('http://','').split('/users/')
        else:
            if '@' in handle:
                username, domain = handle.split('@')
            else:
                return None, None

    return username, domain

cachedWebfingers = {}

def webfingerHandle(session,handle: str,https: bool):
    username, domain = parseHandle(handle)
    if not username:
        return None
    if cachedWebfingers.get(username+'@'+domain):
        return cachedWebfingers[username+'@'+domain]
    prefix='https'
    if not https:
        prefix='http'    
    url = '{}://{}/.well-known/webfinger'.format(prefix,domain)
    par = {'resource': 'acct:{}'.format(username+'@'+domain)}
    hdr = {'Accept': 'application/jrd+json'}
    #try:
    result = getJson(session, url, hdr, par)
    #except:
    #    print("Unable to webfinger " + url)
    #    return None
    cachedWebfingers[username+'@'+domain] = result
    return result

def generateMagicKey(publicKeyPem):
    """See magic_key method in
       https://github.com/tootsuite/mastodon/blob/707ddf7808f90e3ab042d7642d368c2ce8e95e6f/app/models/account.rb
    """
    privkey = RSA.importKey(publicKeyPem)    
    mod = base64.urlsafe_b64encode(number.long_to_bytes(privkey.n)).decode("utf-8")
    pubexp = base64.urlsafe_b64encode(number.long_to_bytes(privkey.e)).decode("utf-8")
    return f"data:application/magic-public-key,RSA.{mod}.{pubexp}"

def storeWebfingerEndpoint(username: str,domain: str,wfJson) -> bool:
    """Stores webfinger endpoint for a user to a file
    """
    handle=username+'@'+domain
    baseDir=os.getcwd()
    wfSubdir='/wfendpoints'
    if not os.path.isdir(baseDir+wfSubdir):
        os.mkdir(baseDir+wfSubdir)
    filename=baseDir+wfSubdir+'/'+handle.lower()+'.json'
    with open(filename, 'w') as fp:
        commentjson.dump(wfJson, fp, indent=4, sort_keys=False)
    return True

def createWebfingerEndpoint(username,domain,https,publicKeyPem) -> {}:
    """Creates a webfinger endpoint for a user
    """
    prefix='https'
    if not https:
        prefix='http'
        
    account = {
        "aliases": [
            prefix+"://"+domain+"/@"+username,
            prefix+"://"+domain+"/users/"+username
        ],
        "links": [
            {
                "href": prefix+"://"+domain+"/@"+username,
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html"
            },
            {
                "href": prefix+"://"+domain+"/users/"+username+".atom",
                "rel": "http://schemas.google.com/g/2010#updates-from",
                "type": "application/atom+xml"
            },
            {
                "href": prefix+"://"+domain+"/users/"+username,
                "rel": "self",
                "type": "application/activity+json"
            },
            {
                "href": prefix+"://"+domain+"/api/salmon/1",
                "rel": "salmon"
            },
            {
                "href": generateMagicKey(publicKeyPem),
                "rel": "magic-public-key"
            },
            {
                "rel": "http://ostatus.org/schema/1.0/subscribe",
                "template": prefix+"://"+domain+"/authorize_interaction?uri={uri}"
            }
        ],
        "subject": "acct:"+username+"@"+domain
    }
    return account

def webfingerMeta() -> str:
    """
    """
    return "<?xml version=’1.0' encoding=’UTF-8'?>" \
        "<XRD xmlns=’http://docs.oasis-open.org/ns/xri/xrd-1.0'" \
        " xmlns:hm=’http://host-meta.net/xrd/1.0'>" \
        "" \
        "<hm:Host>example.com</hm:Host>" \
        "" \
        "<Link rel=’lrdd’" \
        " template=’http://example.com/describe?uri={uri}'>" \
        " <Title>Resource Descriptor</Title>" \
        " </Link>" \
        "</XRD>"

def webfingerLookup(path: str):
    """Lookup the webfinger endpoint for an account
    """
    if not path.startswith('/.well-known/webfinger?'):
        return None
    handle=None
    if 'resource=acct:' in path:
        handle=path.split('resource=acct:')[1].strip()        
    else:
        if 'resource=acct%3A' in path:
            handle=path.split('resource=acct%3A')[1].replace('%40','@').strip()
    if not handle:
        return None
    if '&' in handle:
        handle=handle.split('&')[0].strip()
    if '@' not in handle:
        return None
    baseDir=os.getcwd()
    filename=baseDir+'/wfendpoints/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return None
    wfJson={"user": "unknown"}
    with open(filename, 'r') as fp:
        wfJson=commentjson.load(fp)
    return wfJson
