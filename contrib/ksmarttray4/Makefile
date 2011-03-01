prefix=/usr
kdeprefix=`kde4-config --prefix || echo ${prefix}`

all:

install:
	install -d $(DESTDIR)${kdeprefix}/bin
	install -m 0755 ksmarttray.py $(DESTDIR)${kdeprefix}/bin/ksmarttray
	install -d $(DESTDIR)${prefix}/bin
	install -m 0755 smart-helper $(DESTDIR)${prefix}/bin/smart-helper-kde
	install -d $(DESTDIR)${kdeprefix}/share/applications/kde4
	install -m 0644 ksmarttray.desktop $(DESTDIR)${kdeprefix}/share/applications/kde4/
	install -d $(DESTDIR)${kdeprefix}/share/icons/hicolor/48x48
	install -m 0644 ksmarttray.png ${kdeprefix}/share/icons/hicolor/48x48/

