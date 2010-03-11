import tornado.websocket
class RTSearchHandler(tornado.websocket.WebSocketHandler, auth.SplunkMixin):
    """
    WARNING!!!
    Unstable prototype
    """
    def open(self):
        self.async_request("/services/search/jobs/export", self.on_async_finish, streaming_callback=self.on_async_stream, request_timeout=86400.0, search="search index=_*", earliest_time="rt", latest_time="rt")
        self.receive_message(self.on_message)

    def on_async_stream(self, response):
        self.write_message(u""+response)    

    def on_message(self, message):
       self.write_message(u"You said: " + message)

    def on_async_finish(self, response, **kwargs):
       self.close()