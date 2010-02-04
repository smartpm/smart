

all: html

.PHONY: zip pdf


zip: smart.zip

smart.zip: html
	zip -r -y smart.zip html

html: config.xsl smart.xml
	xmlto xhtml -m config.xsl -o html smart.xml
	mkdir -p html/images
	cp -p *.css html/
	cp -p images/*.png html/images/

pdf: smart.pdf

smart.pdf: smart.xml
	dblatex --param doc.collab.show=0 -o smart.pdf smart.xml

