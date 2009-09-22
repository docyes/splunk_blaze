import tornado.httpserver
import tornado.ioloop
import tornado.web
import os.path

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html")


settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "e220cf903f537500f6cfcaccd64df14d",
    "xsrf_cookies": True,
    "debug": True,
}

application = tornado.web.Application([
    (r"/", MainHandler),
], **settings)

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()