#!/usr/bin/env python

import os.path
import httplib2
import urllib
import io
import datetime
import lxml.etree as et
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import uimodules

from tornado.options import define, options

define("port", default=8888, help="web server port", type=int)
define("debug", default=False, help="web server debug mode", type=bool)
define("search_browser_cache_ttl", default=30000, help="maximum browser cache lifetime for a search", type=int)
define("splunk_host_path", default="https://localhost:8089", help="splunk server scheme://host:port (Use http over https for performance bump!)")
define("splunk_username", default="admin", help="splunk username")
define("splunk_password", default="changeme", help="splunk password")
define("splunk_search_segmentation", default="outer", help="splunk search segmentation, one of inner, outer, full, raw", type=str)
define("splunk_search_spawn_process", default=False, help="splunk search spawns new process", type=bool)
define("splunk_search_query_prefix", default="search index=_* ", help="splunk search query prefix", type=str)
define("splunk_search_query_suffix", default="* | fields | head 10", help="splunk search query suffix", type=str)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/search", SearchHandler),            
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="e220cf903f537500f6cfcaccd64df14d",
            xsrf_cookies=True,
            ui_modules=uimodules,
            search_browser_cache_ttl=options.search_browser_cache_ttl,
            splunk_host_path=options.splunk_host_path,
            splunk_username=options.splunk_username,
            splunk_password=options.splunk_password,
            splunk_search_segmentation=options.splunk_search_segmentation,
            splunk_search_spawn_process=options.splunk_search_spawn_process,
            splunk_search_query_prefix=options.splunk_search_query_prefix,
            splunk_search_query_suffix=options.splunk_search_query_suffix,
            debug=options.debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        #one global raw transformer
        xslt_file = io.open(os.path.join(settings['template_path'], "raw.xslt"), encoding="utf-8")
        self.xslt_transform = et.XSLT(et.XML("".join(xslt_file.readlines())))
        
class BaseHandler(tornado.web.RequestHandler):
    pass
    
class HomeHandler(BaseHandler):
    def get(self):
        self.render("index.html", search_browser_cache_ttl=self.settings.get("search_browser_cache_ttl"), splunk_search_query_prefix=self.settings.get("splunk_search_query_prefix"), splunk_search_query_suffix=self.settings.get("splunk_search_query_suffix"))

class SearchHandler(BaseHandler):
    def get(self):
        h = httplib2.Http(".cache", timeout=1)
        h.add_credentials(self.settings.get('splunk_username'), self.settings.get('splunk_password'))
        data = dict(
            search=self.get_argument("search"),
            spawn_process="1" if options.splunk_search_spawn_process else "0",
            segmentation=options.splunk_search_segmentation,
        )
        resource = "%s/services/search/jobs/oneshot?%s" % (self.settings.get("splunk_host_path"), urllib.urlencode(data))
        resp, content = h.request(resource)
        xml_doc = et.fromstring(content)
        self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(days=365))         
        self.render("search.html", xml_doc=xml_doc, xslt_transform=self.application.xslt_transform, search=self.get_argument("search"))

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
    main()
