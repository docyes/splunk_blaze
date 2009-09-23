#!/usr/bin/env python

import os.path
import time
import splunk.auth
import splunk.search
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import uimodules

from tornado.options import define, options

define("port", default=8888, help="run web server on the given port", type=int)
define("splunk_host_path", default="https://localhost:8089", help="splunk server scheme://host:port (Use http over https for performance bump!)")
define("splunk_username", default="admin", help="splunk user")
define("splunk_password", default="changeme", help="splunk password")

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
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        
        #Have one global splunk session_key accross all users.
        self.session_key = splunk.auth.getSessionKey(options.splunk_username, options.splunk_password, hostPath=options.splunk_host_path)
        
class BaseHandler(tornado.web.RequestHandler):
    @property
    def session_key(self):
        return self.application.session_key
    
class HomeHandler(BaseHandler):
    def get(self):
        self.render("index.html")

class SearchHandler(BaseHandler):
    def post(self):
        job = splunk.search.dispatch(self.get_argument("search"), sessionKey=self.session_key, hostPath=options.splunk_host_path)
        job.setFetchOption(
            segmentationMode='full',
            maxLines=500,
        )
        maxtime = 1
        pause = 0.05
        lapsed = 0.0
        while not job.isDone:
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        xslt = '''<?xml version="1.0" encoding="UTF-8"?>
        <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
            <xsl:strip-space elements="*" />
            <xsl:preserve-space elements="v sg" />
            <xsl:output method="html" indent="no" />
            <xsl:template match="/">
                <xsl:apply-templates select="v" />
            </xsl:template>
            <xsl:template match="v">
                <xsl:apply-templates />
            </xsl:template>
            <xsl:template match="sg">
                <em>
                    <xsl:attribute name="class">
                        <xsl:text>t</xsl:text>
                        <xsl:if test="@h">
                            <xsl:text> a</xsl:text>
                        </xsl:if>
                    </xsl:attribute>
                    <xsl:apply-templates />
                </em>
            </xsl:template>
        </xsl:stylesheet>
        '''
        self.render("search.html", job=job, xslt=xslt)

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
 
 
if __name__ == "__main__":
    main()