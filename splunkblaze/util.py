#!/usr/bin/env python
import urllib
import tornado.escape

def encode_uri_component(value):
    """
    Returns a valid URL-encoded version of the given value following JavaScript encodeURIComponent scheme.
    See http://unspecified.wordpress.com/2008/05/24/uri-encoding/
    """
    return urllib.quote(tornado.escape.utf8(value), safe="~")