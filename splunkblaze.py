#!/usr/bin/env python
import os.path
import urllib
import io
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
define("splunk_host_path", default="https://localhost:8089", help="server scheme://host:port (http is faster than https)")
define("splunk_username", default="admin", help="username")
define("splunk_password", default="changeme", help="password")
define("splunk_search_segmentation", default="outer", help="search segmentation, one of inner, outer, full, raw", type=str)
define("splunk_search_query_prefix", default="search index=_* ", help="search query prefix for sync and async", type=str)
define("splunk_search_async_max_count", default=10000, help="async search number of events that can be accessible in any given status bucket", type=int)
define("splunk_search_async_max_time", default=1, help="async search max runtime in seconds before search is finalized", type=int)
define("splunk_search_async_required_field_list", default=["*"], help="async search required field list, comma seperated", type=str, multiple=True)
define("splunk_search_async_spawn_process", default=True, help="async search spawns new process", type=bool)
define("splunk_search_async_query_suffix", default="*", help="sync search query suffix", type=str)
define("splunk_search_sync_spawn_process", default=False, help="sync search spawns new process", type=bool)
define("splunk_search_sync_query_suffix", default="* | fields", help="sync search query suffix", type=str)
define("splunk_search_sync_max_count", default=10, help="sync search number of events that can be accessible in any given status bucket", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/search/new", SearchHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret="e220cf903f537500f6cfcaccd64df14d",
            xsrf_cookies=True,
            ui_modules=uimodules,
            splunk_host_path=options.splunk_host_path,
            splunk_username=options.splunk_username,
            splunk_password=options.splunk_password,
            debug=options.debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        #shared global attributes 
        self.xslt_transform = et.XSLT(et.parse(os.path.join(settings['template_path'], "search", "_raw.xslt")))
        
class BaseHandler(tornado.web.RequestHandler):
    @property
    def xslt_transform(self):
        return self.application.xslt_transform

class HomeHandler(BaseHandler):
    def get(self):
        self.render("home/index.html", search_browser_cache_ttl=options.search_browser_cache_ttl)
       
class SearchHandler(BaseHandler, auth.SplunkMixin):
    @tornado.web.asynchronous
    def get(self):
        sid = self.get_argument("sid", None)
        if sid:
            self.buffer = self.BufferedWriter(3, self._on_finish)
            self.async_request("/services/search/jobs/%s/control" % sid, self._on_async_search_cancel, session_key=self.session_key, post_args=dict(action="cancel"))
        else:
            self.buffer = self.BufferedWriter(2, self._on_finish)
        #long running async search
        async_post_args = dict(
            max_count = options.splunk_search_async_max_count,
            max_time = options.splunk_search_async_max_time,
            required_field_list = ",".join(options.splunk_search_async_required_field_list),
            search = "%s%s%s" % (options.splunk_search_query_prefix, self.get_argument("search"), options.splunk_search_async_query_suffix),
            segmentation = options.splunk_search_segmentation,
            spawn_process = "1" if options.splunk_search_async_spawn_process else "0"
        )
        self.async_request("/services/search/jobs", self._on_async_search_create, session_key=self.session_key, post_args=async_post_args)
        #short running sync search
        sync_search = "%s%s%s" % (options.splunk_search_query_prefix, self.get_argument("search"), options.splunk_search_sync_query_suffix)
        sync_spawn_process = "1" if options.splunk_search_sync_spawn_process else "0"
        self.async_request("/services/search/jobs/oneshot", self._on_sync_search_create, session_key=self.session_key, count=options.splunk_search_sync_max_count, max_count=options.splunk_search_sync_max_count, search=sync_search, spawn_process=sync_spawn_process, segmentation=options.splunk_search_segmentation)

    def _on_sync_search_create(self, response, xml=None, **kwargs):
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
        self.buffer.write(0, data)

    def _on_async_search_create(self, response, xml=None, **kwargs):
        data = self.render_string("search/_job.html", sid=xml.findtext("sid")) if xml is not None else ""
        self.buffer.write(1, data)
    
    def _on_async_search_cancel(self, response, xml=None, **kwargs):
        data = self.render_string("search/_comment.html", comment="previous search job cancel status message: %s" % xml.findtext("messages/msg"))
        self.buffer.write(2, data)

    def _on_finish(self, string):
        self.finish(string)
    
def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
 
if __name__ == "__main__":
    main()
