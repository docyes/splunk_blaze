import tornado.web

class Event(tornado.web.UIModule):
    def render(self, event):
        return self.render_string("modules/event.html", event=event, xslt_transform=self.handler.xslt_transform)
