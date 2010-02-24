import sys,re


# tmp replacements for ~ T(ilda), - D(ash), * A(sterisk)
# that user is unlikely to ever type.
T = "#TtT#"
D = "#DdD#"
A = "#AaA#"

def processMatches(regex, text, func):
    cleaned = text
    spans = [m.span(1) for m in re.finditer(regex, text)]
    offset = 0
    for start, end in spans:
        val = cleaned[start:end]
        newval = apply(func, [val])
        text = text[0:start+offset] + newval + text[end+offset:]
        offset += len(newval) - len(val)
    return text

def deencode(text):
    return 

def expand(search):

    # change any *,~,- inside of quotes to some temp A,D,T representation
    search = processMatches('(".*?")', search, lambda x: x.replace("*", A).replace("-", D).replace("~", T))

    search = re.sub('(^|\\s*)([^~-]\\S+)($|\\s*)', "\\1\\2*\\3",      search)
    search = re.sub("(\\s*)~(\\S)",                "\\1eventtype=\\2", search)
    search = re.sub("(\\s*)-(\\S)",                "\\1NOT \\2",       search)

    # remove any asterisk(*) inside and around quotes
    search = processMatches('([*]?".*?"[*])', search, lambda x: x.replace("*", ""))
    # revert A,D,T change inside of quotes back to original *,~,-
    search = search.replace(A, "*").replace(D, "-").replace(T, "~").replace("**", "*")
    return search

if __name__ == "__main__":

    ezsearch = ' '.join(sys.argv[1:])
    fullsearch = expand(ezsearch)
    print "EZSEARCH:\t%s\nFULLSEARCH:\t%s" % (ezsearch, fullsearch)
    
