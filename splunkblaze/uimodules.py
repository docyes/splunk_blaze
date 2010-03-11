import tornado.web
import web

class Event(tornado.web.UIModule):
    def render(self, event, display_time=True):
        return self.render_string("modules/event.html", event=event, xslt_transform=self.handler.xslt_transform, display_time=display_time)

class CSSSelector(tornado.web.UIModule):
    def render(self, root="body", class_name=None):
        class_name = class_name if class_name else web.contextual_class_name(self.handler)
        return "%s.%s" % (root, class_name)
