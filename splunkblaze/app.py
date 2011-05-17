#!/usr/bin/env python
import os.path
import datetime
import hashlib
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
import escape
import web
import jsmin
import cssmin
from tornado.options import define, options

#app options
define("port", default=8888, help="web server port", type=int)
define("debug", default=False, help="web server debug mode", type=bool)
define("static_url_prefix", default="/static", help="url prefix for static assets")
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
#async search options
define("splunk_search_async_max_count", default=10000, help="async search number of events that can be accessible in any given status bucket", type=int)
define("splunk_search_async_max_time", default=1, help="async search max runtime in seconds before search is finalized", type=int)
define("splunk_search_async_required_field_list", default=["*"], help="async search required field list, comma separated", type=str, multiple=True)
define("splunk_search_async_spawn_process", default=True, help="async search spawns new process", type=bool)
define("splunk_search_async_query_suffix", default="* | fields", help="sync search query suffix", type=str)
#ui options
define("search_browser_cache_ttl", default=30000, help="maximum browser cache lifetime for a search", type=int)
define("display_event_time", default=True, help="control the display of the event time", type=bool)
define("enable_ezsearch", default=False, help="EXPERIMENTAL!!! use the ezsearch module for simplified search string parsing", type=str)
define("enable_search_loader", default=False, help="control the display of the search loader animation when a search is running", type=bool)
define("enable_clear_button", default=False, help="control the display of the clear button for a search", type=bool)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            tornado.web.url(r"/", HomeHandler),
            tornado.web.url(r"/search/new", SyncSearchHandler, name="search"),
            #tornado.web.url(r"/search/new", ParallelSearchHandler, name="search"),
            tornado.web.url(r"/search/jobs/control", SearchJobControlHandler, name="control"),
        ]
        settings = dict(
            cookie_secret="e220cf903f537500f6cfcaccd64df14d",
            debug=options.debug,
            splunk_host_path=options.splunk_host_path,
            splunk_password=options.splunk_password,
            splunk_username=options.splunk_username,
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            static_url_prefix=options.static_url_prefix,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            ui_modules=uimodules,
            xsrf_cookies=True,
        )
        self.cache = {}
        self.xslt_transform = et.XSLT(et.parse(os.path.join(settings["template_path"], "modules", "raw.xslt")))
        tornado.web.Application.__init__(self, handlers, **settings)
        
class BaseHandler(tornado.web.RequestHandler):
    def digest(self, string):
        hash = hashlib.md5()
        hash.update(string)
        return hash.hexdigest()

    def handler_name(self, obj):
        return obj.__class__.__name__.lower().replace("handler", "")

    def is_xhr(self):
        return True if self.request.headers.get("X-Requested-With")=="XMLHttpRequest" else False

    def render_string(self, template_name, **kwargs):
        args = dict(
             cssmin=cssmin.cssmin,
             digest=self.digest,
             handler_name=self.handler_name(self),
             encode_uri_component=escape.encode_uri_component,
             is_xhr=self.is_xhr,
             jsmin=jsmin.jsmin
        )
        args.update(kwargs)
        return tornado.web.RequestHandler.render_string(self, template_name, **args)
    
    @property
    def xslt_transform(self):
        return self.application.xslt_transform

class HomeHandler(BaseHandler):
    def get(self):
        self.finish(self._render_string())
        
    @web.cache
    def _render_string(self):
         return self.render_string("home/index.html", enable_clear_button=options.enable_clear_button, enable_search_loader=options.enable_search_loader, search_browser_cache_ttl=options.search_browser_cache_ttl)

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
        search = self.get_argument("search")
        if response.error:
            if xml is not None:
                error = xml.findtext("messages/msg")
            else:
                error = response.error
            data = self.render_string("search/_error.html", error=error)    
        elif xml is not None:
            results = xml.findall("result")
            data = self.render_string("search/_results.html", results=results, search=search, count=options.splunk_search_sync_max_count, display_event_time=options.display_event_time)
        else:
            data = self.render_string("search/_none.html")
        data = self.render_string("search/_search.html", search=search) + data
        self.finish(data)

class ParallelSearchHandler(BaseHandler, auth.SplunkMixin):
    """
    Experimental!!!
    """
    @tornado.web.asynchronous
    def get(self):
        sid = self.get_argument("sid", None)
        if sid:
            self.buffer = web.BufferedWriter(4, self._on_finish)
            self.async_search_delete(sid)
        else:
            self.buffer = web.BufferedWriter(3, self._on_finish)
        search_argument = self.get_argument("search")    
        search_string = ezsearch.expand(search_argument) if options.enable_ezsearch else search_argument
        self.sync_search_create(search_string)
        self.async_search_create(search_string)
        self.buffer.write(0, self.render_string("search/_search.html", search=search_argument))
        
    def sync_search_create(self, search_string):
        search = "%s%s%s" % (options.splunk_search_query_prefix, search_string, options.splunk_search_sync_query_suffix)
        spawn_process = "1" if options.splunk_search_sync_spawn_process else "0"
        self.set_header("Expires", datetime.datetime.utcnow() + datetime.timedelta(days=365))
        self.async_request("/services/search/jobs/oneshot", self._on_sync_search_create, session_key=self.session_key, 
                           count=options.splunk_search_sync_max_count, max_count=options.splunk_search_sync_max_count,
                           search=search, spawn_process=spawn_process, segmentation=options.splunk_search_segmentation)
    
    def async_search_create(self, search_string):
        post_args = dict(
            max_count = options.splunk_search_async_max_count,
            max_time = options.splunk_search_async_max_time,
            required_field_list = ",".join(options.splunk_search_async_required_field_list),
            search = "%s%s%s" % (options.splunk_search_query_prefix, search_string, options.splunk_search_async_query_suffix),
            segmentation = options.splunk_search_segmentation,
            spawn_process = "1" if options.splunk_search_async_spawn_process else "0"
        )
        self.async_request("/services/search/jobs", self._on_async_search_create, session_key=self.session_key, post_args=post_args)
    
    def async_search_delete(self, sid):
        self.async_request("/services/search/jobs/%s/control" % sid, self._on_async_search_cancel, session_key=self.session_key, post_args=dict(action="cancel"))

    def _on_sync_search_create(self, response, xml=None, **kwargs):
        if response.error:
            if xml is not None:
                error = xml.findtext("messages/msg")
            else:
                error = response.error
            data = self.render_string("search/_error.html", error=error)
        elif xml is not None:
            results = xml.findall("result")
            data = self.render_string("search/_results.html", results=results, search=self.get_argument("search"), count=options.splunk_search_sync_max_count, display_event_time=options.display_event_time)
        else:
            data = self.render_string("search/_none.html")
        self.buffer.write(1, data)

    def _on_async_search_create(self, response, xml=None, **kwargs):
        data = self.render_string("search/_job.html", sid=xml.findtext("sid")) if xml is not None and xml.findtext("sid") else ""
        self.buffer.write(2, data)
        
    def _on_async_search_cancel(self, response, xml=None, **kwargs):
        data = self.render_string("search/_comment.html", comment="previous search job cancel status message: %s" % xml.findtext("messages/msg"))
        self.buffer.write(3, data)

    def _on_finish(self, string):
        self.finish(string)

class SearchJobControlHandler(BaseHandler, auth.SplunkMixin):
    @tornado.web.asynchronous
    def post(self):
        sid = self.get_argument("sid", None)
        action = self.get_argument("action", None)
        self.async_request("/services/search/jobs/%s/control" % self.get_argument("sid"), self._on_finish, session_key=self.session_key, post_args=dict(action=self.get_argument("action")))
    
    def _on_finish(self, response, xml=None, **kwargs):
        self.finish("")
        
def main():
    tornado.options.parse_command_line()
    tornado.locale.load_translations(os.path.join(os.path.dirname(__file__), "translations")) 
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
