#!/usr/bin/env python

import urllib
import tornado.httpclient
import logging
import lxml.etree as et

class SplunkMixin(object):
    """General splunk services connection mixin with shared authentication and lazy session key updating if stale/non-existant."""
    retry_request = True
    
    def get_session_key(self):
        """Session key getter, elegantly retrieves from application global attributes."""
        if hasattr(self.application, "splunk_session_key"):
            return self.application.splunk_session_key
        else:
            return None
        
    def set_session_key(self, session_key):
        """Session key setter, stores in application global attributes."""
        self.application.splunk_session_key = session_key

    session_key = property(get_session_key, set_session_key)     

    def refresh_session_key(self):
        """Refreshes the session key application global attribute."""
        self.session_key = self.request_session_key()

    def request_url(self, pathname, **kwargs):
        """A fully qualified splunk services uri including encoded get params as **kwargs"""
        self.require_setting("splunk_host_path", "Splunk Connect")
        url = "%s%s" % (self.settings["splunk_host_path"], pathname)
        if kwargs:
            url += "?" + urllib.urlencode(kwargs)
        return url

    def request_headers(self, session_key=None):
        """The splunk request headers with the Authorization session key if provided."""
        headers = {}
        if session_key:
            headers["Authorization"] = "Splunk %s" % session_key
        return headers
    
    def request_session_key(self):
        """Retrieve a session key from the splunk authentication endpoint as a syncronous request."""
        self.retry_splunk_request = False
        self.require_setting("splunk_username", "Splunk Connect")
        self.require_setting("splunk_password", "Splunk Connect")
        post_args = {
          "username": self.settings["splunk_username"],
          "password": self.settings["splunk_password"],
        }
        response, xml, json, text = self.sync_request("/services/auth/login", post_args=post_args)
        if response.error is None and xml is not None:
            logging.info("Successfully retrieved Splunk session_key")
            return xml.findtext("sessionKey")
        else:
            logging.info("Could not retrieve Splunk session_key")
            return None
    
    def sync_request(self, pathname, post_args=None, session_key=None, **kwargs):
        """"
        A simplified syncronous http request method for splunk services.
        Returns a tuple based on parse_response method spec.
        """
        url = self.request_url(pathname, **kwargs)
        headers = self.request_headers(session_key=session_key)
        http = tornado.httpclient.HTTPClient()
        if post_args is not None:
            response = http.fetch(url, method="POST", body=urllib.urlencode(post_args), headers=headers)
        else:
            response = http.fetch(url, headers=headers)
        if response.error:
            if response.error.code==401 and self.retry_request:
                self.refresh_session_key()
                return self.sync_request(pathname, post_args=post_args, session_key=self.session_key, **kwargs)
        xml, json, text = self.parse_response(response)
        return response, xml, json, text
 
    def async_request(self, pathname, callback, post_args=None, session_key=None, streaming_callback=None, request_timeout=20.0, **kwargs):
        """
        A simplified non-blocking asynchronous http request method for splunk services. 
        The callback is called with a response, and xml, json, and text keyword args where xml, json, and text are not passed if not serializable from response/content-type.
        """
        url = self.request_url(pathname, **kwargs)
        headers = self.request_headers(session_key=session_key)
        callback=self.async_callback(self._on_async_response, pathname, callback, post_args=post_args, session_key=session_key, streaming_callback=streaming_callback, request_timeout=request_timeout, **kwargs)
        http = tornado.httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args), callback=callback, headers=headers, streaming_callback=streaming_callback, request_timeout=request_timeout)
        else:
            http.fetch(url, callback=callback, headers=headers, streaming_callback=streaming_callback, request_timeout=request_timeout)

    def _on_async_response(self, pathname, callback, response, post_args=None, session_key=None, streaming_callback=None, request_timeout=20.0, **kwargs):
        """Reponse handler for asynchronous requests."""
        if self.request.connection.stream.closed():
            return
        else:
            if response.error:
                if response.error.code==401 and self.retry_request:
                    self.refresh_session_key()
                    if self.session_key:
                        logging.info("Retry request with fresh session key")
                        self.async_request(pathname, callback, post_args=post_args, session_key=self.session_key, streaming_callback=streaming_callback, request_timeout=request_timeout, **kwargs)
                        return
                    else:
                        callback(response)
                        return
            xml, json, text = self.parse_response(response)
            callback(response, xml=xml, json=json, text=text)    

    def parse_response(self, response):
        """
        General splunk http response parser based on reponse content-type.
        Returns a tuple xml, json and text where xml, json and text are None type if not serializable from response/content-type.
        """
        content = response.headers.get("Content-Type", "")    
        if content.find("text/xml")!=-1:
            try:
                xml = et.fromstring(response.body)
            except:
                logging.warning("Could not parse xml")
                return None, None, None
            return xml, None, None
        elif content.find("application/json")!=-1:
            try:
                json = escape.json_decode(response.body)
            except:
                logging.warning("Could not decode json")
                return None, None, None
            return None, json, None
        elif content.find("text/plain")!=-1:
            return None, None, response.body
        else:
            return None, None, None
