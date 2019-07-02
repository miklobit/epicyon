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
from cache import storeWebfingerInCache
from cache import getWebfingerFromCache

def parseHandle(handle: str) -> (str,str):
    if '.' not in handle:
        return None, None
    if '/@' in handle:
        domain, username = \
            handle.replace('https://','').replace('http://','').split('/@')
    else:
        if '/users/' in handle:
            domain, username = \
                handle.replace('https://','').replace('http://','').split('/users/')
        else:
            if '@' in handle:
                username, domain = handle.split('@')
            else:
                return None, None

    return username, domain


def webfingerHandle(session,handle: str,https: bool,cachedWebfingers: {}) -> {}:
    username, domain = parseHandle(handle)
    if not username:
        return None
    wfDomain=domain
    if ':' in wfDomain:
        wfDomain=wfDomain.split(':')[0]
    print('***********cachedWebfingers '+str(cachedWebfingers))
    wf=getWebfingerFromCache(username+'@'+wfDomain,cachedWebfingers)
    if wf:
        return wf
    prefix='https'
    if not https:
        prefix='http'
    url = '{}://{}/.well-known/webfinger'.format(prefix,domain)
    par = {'resource': 'acct:{}'.format(username+'@'+wfDomain)}
    hdr = {'Accept': 'application/jrd+json'}
    #try:
    result = getJson(session, url, hdr, par)
    #except:
    #    print("Unable to webfinger " + url + ' ' + str(hdr) + ' ' + str(par))
    storeWebfingerInCache(username+'@'+wfDomain,result,cachedWebfingers)
    return result

def generateMagicKey(publicKeyPem) -> str:
    """See magic_key method in
       https://github.com/tootsuite/mastodon/blob/707ddf7808f90e3ab042d7642d368c2ce8e95e6f/app/models/account.rb
    """
    privkey = RSA.importKey(publicKeyPem)    
    mod = base64.urlsafe_b64encode(number.long_to_bytes(privkey.n)).decode("utf-8")
    pubexp = base64.urlsafe_b64encode(number.long_to_bytes(privkey.e)).decode("utf-8")
    return f"data:application/magic-public-key,RSA.{mod}.{pubexp}"

def storeWebfingerEndpoint(username: str,domain: str,baseDir: str, \
                           wfJson: {}) -> bool:
    """Stores webfinger endpoint for a user to a file
    """
    handle=username+'@'+domain
    wfSubdir='/wfendpoints'
    if not os.path.isdir(baseDir+wfSubdir):
        os.mkdir(baseDir+wfSubdir)
    filename=baseDir+wfSubdir+'/'+handle.lower()+'.json'
    with open(filename, 'w') as fp:
        commentjson.dump(wfJson, fp, indent=4, sort_keys=False)
    return True

def createWebfingerEndpoint(username: str,domain: str,port: int, \
                            https: bool,publicKeyPem) -> {}:
    """Creates a webfinger endpoint for a user
    """
    prefix='https'
    if not https:
        prefix='http'
        
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

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

def webfingerLookup(path: str,baseDir: str) -> {}:
    """Lookup the webfinger endpoint for an account
    """
    print('############### _webfinger lookup 1')
    if not path.startswith('/.well-known/webfinger?'):
        return None
    print('############### _webfinger lookup 2')
    handle=None
    if 'resource=acct:' in path:
        print('############### _webfinger lookup 3')
        handle=path.split('resource=acct:')[1].strip()        
    else:
        print('############### _webfinger lookup 4')
        if 'resource=acct%3A' in path:
            print('############### _webfinger lookup 5')
            handle=path.split('resource=acct%3A')[1].replace('%40','@').strip()            
    print('############### _webfinger lookup 6')
    if not handle:
        return None
    print('############### _webfinger lookup 7')
    if '&' in handle:
        handle=handle.split('&')[0].strip()
    print('############### _webfinger lookup 8')
    if '@' not in handle:
        return None
    filename=baseDir+'/wfendpoints/'+handle.lower()+'.json'
    print('############### _webfinger lookup 9: '+filename)
    if not os.path.isfile(filename):
        return None
    print('############### _webfinger lookup 10')
    wfJson={"user": "unknown"}
    with open(filename, 'r') as fp:
        wfJson=commentjson.load(fp)
    return wfJson
