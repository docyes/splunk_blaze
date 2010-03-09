#!/usr/bin/env python
import os.path
import datetime
import logging
import lxml.etree as et
import tornado.httpserver
import tornado.ioloop
import tornado.locale
import tornado.options
import tornado.web
import uimodules
import ezsearch
import auth
import util
from tornado.options import define, options

#app options
define("port", default=8888, help="web server port", type=int)
define("debug", default=False, help="web server debug mode", type=bool)
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
#ui options
define("search_browser_cache_ttl", default=30000, help="maximum browser cache lifetime for a search", type=int)
define("display_event_time", default=True, help="control the display of the event time", type=bool)
define("enable_ezsearch", default=False, help="EXPERIMENTAL!!! use the ezsearch module for simplified search string parsing", type=str)
define("enable_search_loader", default=False, help="control the display of the search loader animation when a search is running", type=bool)
define("enable_clear_button", default=False, help="control the display of the clear button for a search", type=bool)

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
        self.xslt_transform = et.XSLT(et.parse(os.path.join(settings["template_path"], "modules", "raw.xslt")))
        tornado.web.Application.__init__(self, handlers, **settings)
        
class BaseHandler(tornado.web.RequestHandler):
    @property
    def xslt_transform(self):
        return self.application.xslt_transform

class HomeHandler(BaseHandler):
    def get(self):
        self.render("home/index.html", enable_clear_button=options.enable_clear_button, enable_search_loader=options.enable_search_loader, search_browser_cache_ttl=options.search_browser_cache_ttl)

class SyncSearchHandler(BaseHandler, auth.SplunkMixin):
    @tornado.web.asynchronous
    def get(self):
        search = self.get_argument("search")
        search = ezsearch.expand(search) if options.enable_ezsearch else search
        sync_search = "%s%s%s" % (options.splunk_search_query_prefix, search, options.splunk_search_sync_query_suffix)
        sync_spawn_process = "1" if options.splunk_search_sync_spawn_process else "0"
        self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(days=365))
        self.async_request("/services/search/jobs/oneshot", self._on_create, session_key=self.session_key, 
                           count=options.splunk_search_sync_max_count, max_count=options.splunk_search_sync_max_count, 
                           search=sync_search, spawn_process=sync_spawn_process, segmentation=options.splunk_search_segmentation)

    def _on_create(self, response, xml=None, **kwargs):
        if response.error:
            if xml is not None:
                error = xml.findtext("messages/msg")
            else:
                error = response.error
            data = self.render_string("search/_error.html", error=error, search=self.get_argument("search"), encode_uri_component=util.encode_uri_component)
        elif xml is not None:
            data = self.render_string("search/_results.html", xml_doc=xml, search=self.get_argument("search"), count=options.splunk_search_sync_max_count, display_event_time=options.display_event_time, encode_uri_component=util.encode_uri_component)
        else:
            data = self.render_string("search/_none.html", search=self.get_argument("search"), encode_uri_component=util.encode_uri_component)
        self.finish(data)

def main():
    tornado.options.parse_command_line()
    tornado.locale.load_translations(os.path.join(os.path.dirname(__file__), "translations")) 
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
 
if __name__ == "__main__":
    main()
