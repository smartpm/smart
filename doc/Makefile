

all: html

.PHONY: zip pdf


zip: smart.zip

smart.zip: html
	zip -r -y smart.zip html

html: smart.xml
	xmlto xhtml -o html smart.xml
	mkdir -p html/images
	cp -p images/*.png html/images/

pdf: smart.pdf

smart.pdf: smart.xml
	dblatex --param doc.collab.show=0 -o smart.pdf smart.xml

