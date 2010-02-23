#!/usr/bin/env python
import sys,re

def expand(search):
    """
    ~news   ------>  news OR "flash:" OR "breaking:"
    // middle east
    ~me      -------> iraq* OR iran* OR syria* OR arabia* OR leban* OR israel* OR palestin*
    ~movies  ------> movie* OR film* OR cinema*
    ~tv ---------> tv OR  television OR t.v.
    ~video     -----> hulu OR netflix OR youtube
     // this would be a massive search!  but now it's just ~media!!  i'm lovin it!
    ~media      ------> ~video OR ~tv OR ~movies OR ~music
    ~games ---------> xbox OR x-box OR wii OR ps2 OR ps-2 OR ps-3 OR ps3 OR nintendo OR ds

    now wildcards anything not quoted,
    handles quotes properly,
    replaces " ~" with eventtype=,
    replace " -" with "NOT "
    it's actually more sophisticated in that they can also be at beginning of the search and don't need a space in front.
    
    $ python ezsearch.py '~foo ~"foo" "baz" -"bart bag foo" ~barf'                                                                                                                          
    EZSEARCH:       ~foo ~"foo" "baz" -"bart bag foo" ~barf                                                                                                                                             
    FULLSEARCH:     eventtype=*foo* eventtype="foo" "baz" NOT "bart bag foo" eventtype=*barf*
    """
    search = re.sub('(^|\\s*)([^~-]\\S+)($|\\s*)', "\\1\\2*\\3",      search)     
    #search = re.sub('(^|\\s*)([^~-]\\S+)($|\\s*)', "\\1*\\2*\\3",      search)
    search = re.sub("(\\s*)~(\\S)",                "\\1eventtype=\\2", search)
    search = re.sub("(\\s*)-(\\S)",                "\\1NOT \\2",       search)

    # remove any asterisk(*) inside and around quotes
    cleaned = search
    spans = [m.span(1) for m in re.finditer('([*]".*?"[*])', search)]
    offset = 0
    for start, end in spans:
        val = cleaned[start:end]
        newval = val.replace("*", "")
        search = search[0:start+offset] + newval + search[end+offset:]
        offset += len(newval) - len(val)
    return search

if __name__ == "__main__":

    ezsearch = ' '.join(sys.argv[1:])
    fullsearch = expand(ezsearch)
    print "EZSEARCH:\t%s\nFULLSEARCH:\t%s" % (ezsearch, fullsearch)
