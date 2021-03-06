__filename__ = "httpsig.py"
__author__ = "Bob Mottram"
__credits__ = ['lamia']
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

# see https://tools.ietf.org/html/draft-cavage-http-signatures-06
#
# This might change in future
# see https://tools.ietf.org/html/draft-ietf-httpbis-message-signatures-01

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import utils as hazutils
import calendar
import base64
from time import gmtime, strftime
import datetime
from utils import getFullDomain
from utils import getSHA256


def messageContentDigest(messageBodyJsonStr: str) -> str:
    msg = messageBodyJsonStr.encode('utf-8')
    hashResult = getSHA256(msg)
    return base64.b64encode(hashResult).decode('utf-8')


def signPostHeaders(dateStr: str, privateKeyPem: str,
                    nickname: str,
                    domain: str, port: int,
                    toDomain: str, toPort: int,
                    path: str,
                    httpPrefix: str,
                    messageBodyJsonStr: str) -> str:
    """Returns a raw signature string that can be plugged into a header and
    used to verify the authenticity of an HTTP transmission.
    """
    domain = getFullDomain(domain, port)

    toDomain = getFullDomain(toDomain, toPort)

    if not dateStr:
        dateStr = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    keyID = httpPrefix + '://' + domain + '/users/' + nickname + '#main-key'
    if not messageBodyJsonStr:
        headers = {
            '(request-target)': f'post {path}',
            'host': toDomain,
            'date': dateStr,
            'content-type': 'application/json'
        }
    else:
        bodyDigest = messageContentDigest(messageBodyJsonStr)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '(request-target)': f'post {path}',
            'host': toDomain,
            'date': dateStr,
            'digest': f'SHA-256={bodyDigest}',
            'content-type': 'application/activity+json',
            'content-length': str(contentLength)
        }
    key = load_pem_private_key(privateKeyPem.encode('utf-8'),
                               None, backend=default_backend())
    # headers.update({
    #     '(request-target)': f'post {path}',
    # })
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
    signedHeaderText = signedHeaderText.strip()
    # signedHeaderText.encode('ascii') matches
    headerDigest = getSHA256(signedHeaderText.encode('ascii'))
    # print('headerDigest2: ' + str(headerDigest))

    # Sign the digest
    rawSignature = key.sign(headerDigest,
                            padding.PKCS1v15(),
                            hazutils.Prehashed(hashes.SHA256()))
    signature = base64.b64encode(rawSignature).decode('ascii')

    # Put it into a valid HTTP signature format
    signatureDict = {
        'keyId': keyID,
        'algorithm': 'rsa-sha256',
        'headers': ' '.join(signedHeaderKeys),
        'signature': signature
    }
    signatureHeader = ','.join(
        [f'{k}="{v}"' for k, v in signatureDict.items()])
    return signatureHeader


def signPostHeadersNew(dateStr: str, privateKeyPem: str,
                       nickname: str,
                       domain: str, port: int,
                       toDomain: str, toPort: int,
                       path: str,
                       httpPrefix: str,
                       messageBodyJsonStr: str,
                       algorithm: str) -> (str, str):
    """Returns a raw signature strings that can be plugged into a header
    as "Signature-Input" and "Signature"
    used to verify the authenticity of an HTTP transmission.
    See https://tools.ietf.org/html/draft-ietf-httpbis-message-signatures-01
    """
    domain = getFullDomain(domain, port)

    toDomain = getFullDomain(toDomain, toPort)

    timeFormat = "%a, %d %b %Y %H:%M:%S %Z"
    if not dateStr:
        currTime = gmtime()
        secondsSinceEpoch = int(calendar.timegm(currTime))
        dateStr = strftime(timeFormat, currTime)
    else:
        currTime = datetime.datetime.strptime(dateStr, timeFormat)
        secondsSinceEpoch = int(currTime.timestamp())
    keyID = httpPrefix + '://' + domain + '/users/' + nickname + '#main-key'
    if not messageBodyJsonStr:
        headers = {
            '*request-target': f'post {path}',
            '*created': str(secondsSinceEpoch),
            'host': toDomain,
            'date': dateStr,
            'content-type': 'application/json'
        }
    else:
        bodyDigest = messageContentDigest(messageBodyJsonStr)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '*request-target': f'post {path}',
            '*created': str(secondsSinceEpoch),
            'host': toDomain,
            'date': dateStr,
            'digest': f'SHA-256={bodyDigest}',
            'content-type': 'application/activity+json',
            'content-length': str(contentLength)
        }
    key = load_pem_private_key(privateKeyPem.encode('utf-8'),
                               None, backend=default_backend())
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
    signedHeaderText = signedHeaderText.strip()
    headerDigest = getSHA256(signedHeaderText.encode('ascii'))

    # Sign the digest. Potentially other signing algorithms can be added here.
    signature = ''
    if algorithm == 'rsa-sha256':
        rawSignature = key.sign(headerDigest,
                                padding.PKCS1v15(),
                                hazutils.Prehashed(hashes.SHA256()))
        signature = base64.b64encode(rawSignature).decode('ascii')

    sigKey = 'sig1'
    # Put it into a valid HTTP signature format
    signatureInputDict = {
        'keyId': keyID,
    }
    signatureIndexHeader = '; '.join(
        [f'{k}="{v}"' for k, v in signatureInputDict.items()])
    signatureIndexHeader += '; alg=hs2019'
    signatureIndexHeader += '; created=' + str(secondsSinceEpoch)
    signatureIndexHeader += \
        '; ' + sigKey + '=(' + ', '.join(signedHeaderKeys) + ')'
    signatureDict = {
        sigKey: signature
    }
    signatureHeader = '; '.join(
        [f'{k}=:{v}:' for k, v in signatureDict.items()])
    return signatureIndexHeader, signatureHeader


def createSignedHeader(privateKeyPem: str, nickname: str,
                       domain: str, port: int,
                       toDomain: str, toPort: int,
                       path: str, httpPrefix: str, withDigest: bool,
                       messageBodyJsonStr: str) -> {}:
    """Note that the domain is the destination, not the sender
    """
    contentType = 'application/activity+json'
    headerDomain = getFullDomain(toDomain, toPort)

    dateStr = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    if not withDigest:
        headers = {
            '(request-target)': f'post {path}',
            'host': headerDomain,
            'date': dateStr
        }
        signatureHeader = \
            signPostHeaders(dateStr, privateKeyPem, nickname,
                            domain, port, toDomain, toPort,
                            path, httpPrefix, None)
    else:
        bodyDigest = messageContentDigest(messageBodyJsonStr)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '(request-target)': f'post {path}',
            'host': headerDomain,
            'date': dateStr,
            'digest': f'SHA-256={bodyDigest}',
            'content-length': str(contentLength),
            'content-type': contentType
        }
        signatureHeader = \
            signPostHeaders(dateStr, privateKeyPem, nickname,
                            domain, port,
                            toDomain, toPort,
                            path, httpPrefix, messageBodyJsonStr)
    headers['signature'] = signatureHeader
    return headers


def _verifyRecentSignature(signedDateStr: str) -> bool:
    """Checks whether the given time taken from the header is within
    12 hours of the current time
    """
    currDate = datetime.datetime.utcnow()
    dateFormat = "%a, %d %b %Y %H:%M:%S %Z"
    signedDate = datetime.datetime.strptime(signedDateStr, dateFormat)
    timeDiffSec = (currDate - signedDate).seconds
    # 12 hours tollerance
    if timeDiffSec > 43200:
        print('WARN: Header signed too long ago: ' + signedDateStr)
        print(str(timeDiffSec / (60 * 60)) + ' hours')
        return False
    if timeDiffSec < 0:
        print('WARN: Header signed in the future! ' + signedDateStr)
        print(str(timeDiffSec / (60 * 60)) + ' hours')
        return False
    return True


def verifyPostHeaders(httpPrefix: str, publicKeyPem: str, headers: dict,
                      path: str, GETmethod: bool,
                      messageBodyDigest: str,
                      messageBodyJsonStr: str, debug: bool,
                      noRecencyCheck=False) -> bool:
    """Returns true or false depending on if the key that we plugged in here
    validates against the headers, method, and path.
    publicKeyPem - the public key from an rsa key pair
    headers - should be a dictionary of request headers
    path - the relative url that was requested from this site
    GETmethod - GET or POST
    messageBodyJsonStr - the received request body (used for digest)
    """

    if GETmethod:
        method = 'GET'
    else:
        method = 'POST'

    if debug:
        print('DEBUG: verifyPostHeaders ' + method)

    pubkey = load_pem_public_key(publicKeyPem.encode('utf-8'),
                                 backend=default_backend())
    # Build a dictionary of the signature values
    if headers.get('Signature-Input'):
        signatureHeader = headers['Signature-Input']
        fieldSep2 = ','
        # split the signature input into separate fields
        signatureDict = {
            k.strip(): v.strip()
            for k, v in [i.split('=', 1) for i in signatureHeader.split(';')]
        }
        requestTargetKey = None
        requestTargetStr = None
        for k, v in signatureDict.items():
            if v.startswith('('):
                requestTargetKey = k
                requestTargetStr = v[1:-1]
                break
        if not requestTargetKey:
            return False
        signatureDict[requestTargetKey] = requestTargetStr
    else:
        requestTargetKey = 'headers'
        signatureHeader = headers['signature']
        fieldSep2 = ' '
        # split the signature input into separate fields
        signatureDict = {
            k: v[1:-1]
            for k, v in [i.split('=', 1) for i in signatureHeader.split(',')]
        }

    # Unpack the signed headers and set values based on current headers and
    # body (if a digest was included)
    signedHeaderList = []
    for signedHeader in signatureDict[requestTargetKey].split(fieldSep2):
        signedHeader = signedHeader.strip()
        if debug:
            print('DEBUG: verifyPostHeaders signedHeader=' + signedHeader)
        if signedHeader == '(request-target)':
            # original Mastodon http signature
            appendStr = f'(request-target): {method.lower()} {path}'
            signedHeaderList.append(appendStr)
        elif '*request-target' in signedHeader:
            # https://tools.ietf.org/html/
            # draft-ietf-httpbis-message-signatures-01
            appendStr = f'*request-target: {method.lower()} {path}'
            # remove ()
            # if appendStr.startswith('('):
            #     appendStr = appendStr.split('(')[1]
            #     if ')' in appendStr:
            #         appendStr = appendStr.split(')')[0]
            signedHeaderList.append(appendStr)
        elif signedHeader == 'digest':
            if messageBodyDigest:
                bodyDigest = messageBodyDigest
            else:
                bodyDigest = messageContentDigest(messageBodyJsonStr)
            signedHeaderList.append(f'digest: SHA-256={bodyDigest}')
        elif signedHeader == 'content-length':
            if headers.get(signedHeader):
                appendStr = f'content-length: {headers[signedHeader]}'
                signedHeaderList.append(appendStr)
            else:
                if headers.get('Content-Length'):
                    contentLength = headers['Content-Length']
                    signedHeaderList.append(f'content-length: {contentLength}')
                else:
                    if headers.get('Content-length'):
                        contentLength = headers['Content-length']
                        appendStr = f'content-length: {contentLength}'
                        signedHeaderList.append(appendStr)
                    else:
                        if debug:
                            print('DEBUG: verifyPostHeaders ' + signedHeader +
                                  ' not found in ' + str(headers))
        else:
            if headers.get(signedHeader):
                if signedHeader == 'date' and not noRecencyCheck:
                    if not _verifyRecentSignature(headers[signedHeader]):
                        if debug:
                            print('DEBUG: ' +
                                  'verifyPostHeaders date is not recent ' +
                                  headers[signedHeader])
                        return False
                signedHeaderList.append(
                    f'{signedHeader}: {headers[signedHeader]}')
            else:
                signedHeaderCap = signedHeader.capitalize()
                if signedHeaderCap == 'Date':
                    if not _verifyRecentSignature(headers[signedHeaderCap]):
                        if debug:
                            print('DEBUG: ' +
                                  'verifyPostHeaders date is not recent ' +
                                  headers[signedHeader])
                        return False
                if headers.get(signedHeaderCap):
                    signedHeaderList.append(
                        f'{signedHeader}: {headers[signedHeaderCap]}')

    if debug:
        print('DEBUG: signedHeaderList: ' + str(signedHeaderList))
    # Now we have our header data digest
    signedHeaderText = '\n'.join(signedHeaderList)
    headerDigest = getSHA256(signedHeaderText.encode('ascii'))

    # Get the signature, verify with public key, return result
    signature = None
    if headers.get('Signature-Input') and headers.get('Signature'):
        # https://tools.ietf.org/html/
        # draft-ietf-httpbis-message-signatures-01
        headersSig = headers['Signature']
        # remove sig1=:
        if requestTargetKey + '=:' in headersSig:
            headersSig = headersSig.split(requestTargetKey + '=:')[1]
            headersSig = headersSig[:len(headersSig)-1]
        signature = base64.b64decode(headersSig)
    else:
        # Original Mastodon signature
        signature = base64.b64decode(signatureDict['signature'])

    try:
        pubkey.verify(
            signature,
            headerDigest,
            padding.PKCS1v15(),
            hazutils.Prehashed(hashes.SHA256()))
        return True
    except BaseException:
        if debug:
            print('DEBUG: verifyPostHeaders pkcs1_15 verify failure')
        return False
