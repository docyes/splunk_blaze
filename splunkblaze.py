#!/usr/bin/env python

import os.path
import urllib
import io
import datetime
import lxml.etree as et
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import uimodules
import auth

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
            (r"/search/sync", SyncSearchHandler),    
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
        xslt_file = io.open(os.path.join(settings['template_path'], "raw.xslt"), encoding="utf-8")
        #shared global attributes 
        self.xslt_transform = et.XSLT(et.XML("".join(xslt_file.readlines())))
        
class BaseHandler(tornado.web.RequestHandler):
    @property
    def xslt_transform(self):
        return self.application.xslt_transform

class HomeHandler(BaseHandler):
    def get(self):
        self.render("index.html", search_browser_cache_ttl=self.settings.get("search_browser_cache_ttl"), splunk_search_query_prefix=self.settings.get("splunk_search_query_prefix"), splunk_search_query_suffix=self.settings.get("splunk_search_query_suffix"))
            
class SyncSearchHandler(BaseHandler, auth.SplunkMixin):
    @tornado.web.asynchronous
    def get(self):
        spawn_process = "1" if options.splunk_search_spawn_process else "0"
        self.async_request("/services/search/jobs/oneshot", self._on_result, session_key=self.session_key, search=self.get_argument("search"), spawn_process=spawn_process, segmentation=options.splunk_search_segmentation)
    def _on_result(self, response, xml=None, **kwargs):
        if response.error:
            if xml is not None:
                error =  xml.findtext("messages/msg")
                self.write(tornado.escape.xhtml_unescape("<!-- error %s -->" % error))
            else:
                self.write("Blockage in cave! %s" % response.error)
            self.finish()
        elif xml is not None:
            self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(days=365))
            self.render("search.html", xml_doc=xml, xslt_transform=self.xslt_transform, search=self.get_argument("search"))
        else:
            self.write(tornado.escape.xhtml_unescape("<!-- no results -->"))
            self.finish()

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start() 
 
if __name__ == "__main__":
    main()
