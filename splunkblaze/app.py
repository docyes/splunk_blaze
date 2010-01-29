#!/usr/bin/env python
import os.path
import urllib
import io
import datetime
import logging
import lxml.etree as et
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import uimodules
import auth
from tornado.options import define, options

#app options
define("port", default=8888, help="web server port", type=int)
define("debug", default=False, help="web server debug mode", type=bool)
define("search_browser_cache_ttl", default=30000, help="maximum browser cache lifetime for a search", type=int)
#splunkd options
define("splunk_host_path", default="http://localhost:8089", help="server scheme://host:port (http is faster than https)")
define("splunk_username", default="admin", help="username")
define("splunk_password", default="changeme", help="password")
#shared search options
define("splunk_search_segmentation", default="inner", help="search segmentation, one of inner, outer, full, raw", type=str)
define("splunk_search_query_prefix", default="search index=_* ", help="search query prefix for sync and async", type=str)
#sync search options
define("splunk_search_sync_spawn_process", default=False, help="sync search spawns new process", type=bool)
define("splunk_search_sync_query_suffix", default="* | fields", help="sync search query suffix", type=str)
define("splunk_search_sync_max_count", default=10, help="sync search number of events that can be accessible in any given status bucket", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/search/new", SyncSearchHandler),
        ]
        settings = dict(
            cookie_secret="e220cf903f537500f6cfcaccd64df14d",
            debug=options.debug,
            splunk_host_path=options.splunk_host_path,
            splunk_password=options.splunk_password,
            splunk_username=options.splunk_username,
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules=uimodules,
            xsrf_cookies=True,
        )
        self.xslt_transform = et.XSLT(et.parse(os.path.join(settings["template_path"], "search", "_raw.xslt")))
        tornado.web.Application.__init__(self, handlers, **settings)
        
class BaseHandler(tornado.web.RequestHandler):
    @property
    def xslt_transform(self):
        return self.application.xslt_transform

class HomeHandler(BaseHandler):
    def get(self):
        self.render("home/index.html", search_browser_cache_ttl=options.search_browser_cache_ttl)

class SyncSearchHandler(BaseHandler, auth.SplunkMixin):
    @tornado.web.asynchronous
    def get(self):
        sync_search = "%s%s%s" % (options.splunk_search_query_prefix, self.get_argument("search"), options.splunk_search_sync_query_suffix)
        sync_spawn_process = "1" if options.splunk_search_sync_spawn_process else "0"
        self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(days=365))
        self.async_request("/services/search/jobs/oneshot", self._on_create, session_key=self.session_key, count=options.splunk_search_sync_max_count, max_count=options.splunk_search_sync_max_count, search=sync_search, spawn_process=sync_spawn_process, segmentation=options.splunk_search_segmentation)

    def _on_create(self, response, xml=None, **kwargs):
        if response.error:
            if xml is not None:
                error = xml.findtext("messages/msg")
            else:
                error = response.error
            data = self.render_string("search/_error.html", error=error)
        elif xml is not None:
            data = self.render_string("search/_results.html", xml_doc=xml, xslt_transform=self.xslt_transform, search=self.get_argument("search"), count=options.splunk_search_sync_max_count)
        else:
            data = self.render_string("search/_comment.html", comment="no results for search")
        self.finish(data)

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
 
if __name__ == "__main__":
    main()