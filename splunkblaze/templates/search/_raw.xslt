<?xml version="1.0" encoding="UTF-8"?>
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