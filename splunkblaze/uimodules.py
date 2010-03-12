import tornado.web

class Event(tornado.web.UIModule):
    def render(self, event, display_time=True):
        return self.render_string("modules/event.html", event=event, xslt_transform=self.handler.xslt_transform, display_time=display_time)

