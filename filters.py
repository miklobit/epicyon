__filename__ = "filters.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os

def addFilter(baseDir: str,nickname: str,domain: str,words: str) -> bool:
    """Adds a filter for particular words within the content of a incoming posts
    """
    filtersFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/filters.txt'
    if os.path.isfile(filtersFilename):
        if words in open(filtersFilename).read():
            return False
    filtersFile=open(filtersFilename, "a+")
    filtersFile.write(words+'\n')
    filtersFile.close()
    return True

def removeFilter(baseDir: str,nickname: str,domain: str, \
                 words: str) -> bool:
    """Removes a word filter
    """
    filtersFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/filters.txt'
    if os.path.isfile(filtersFilename):
        if words in open(filtersFilename).read():
            with open(filtersFilename, 'r') as fp:
                with open(filtersFilename+'.new', 'w') as fpnew:
                    for line in fp:
                        line=line.replace('\n','')
                        if words not in line:
                            fpnew.write(line+'\n')
            if os.path.isfile(filtersFilename+'.new'):
                os.rename(filtersFilename+'.new',filtersFilename)
                return True
    return False
                    
def isFiltered(baseDir: str,nickname: str,domain: str,content: str) -> bool:
    """Should the given content be filtered out?
    This is a simple type of filter which just matches words, not a regex
    You can add individual words or use word1+word2 to indicate that two
    words must be present although not necessarily adjacent
    """
    filtersFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/filters.txt'
    if os.path.isfile(filtersFilename):
        with open(filtersFilename, 'r') as fp:
            for line in fp:
                filterStr=line.replace('\n','')
                if '+' not in filterStr:
                    if filterStr in content:
                        return True
                else:
                    filterWords=filterStr.replace('"','').split('+')
                    for word in filterWords:
                        if not word in content:
                            return False
                    return True
    return False

