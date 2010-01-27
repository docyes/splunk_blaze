# Copyright 1999-2010 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils

DESCRIPTION="A blazingly fast frontend with arrow key bindings using the Facebook http://www.tornadoweb.org web framework and http://www.splunk.com search engine."
HOMEPAGE="http://github.com/docyes/splunk_blaze"
SRC_URI="http://github.com/docyes/splunk_blaze.git"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

RDEPEND="www-servers/tornado
	dev-python/lxml
"

src_install() {
    newinitd "${FILESDIR}/splunkblazed.init" splunkblazed
}