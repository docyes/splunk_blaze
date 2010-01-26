#!/usr/bin/env python

import distutils.core
import sys

distutils.core.setup(
    name = "splunkblaze",
    version = "9999",
    description = "A blazingly fast frontend using Tornado for the Splunk search engine",
    author = "Carl S. Yestrau Jr.",
    author_email = "spam@featureblend.com",
    url = "http://github.com/docyes/splunk_blaze",
    py_modules = ['auth', 'splunkblaze', 'uimodules']
)
