import tornado.httpserver
import tornado.ioloop
import tornado.web
import uimodules
import os.path
import time
import splunk.auth
import splunk.search

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html")

class SearchHandler(tornado.web.RequestHandler):
    def post(self):
        session_key = splunk.auth.getSessionKey("admin", "changeme", hostPath="http://localhost:8089")
        job = splunk.search.dispatch(self.get_argument("search"), sessionKey=session_key, hostPath="http://localhost:8089")
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
        self.render("templates/search.html", job=job, xslt=xslt)

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "e220cf903f537500f6cfcaccd64df14d",
    "xsrf_cookies": True,
    "debug": True,
    "ui_modules": uimodules,
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/search", SearchHandler),
], **settings)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
    