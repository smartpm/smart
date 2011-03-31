all:

clean:

install:
	install -d $(DESTDIR)/usr/bin
	install -m 0755 smart-applet.py $(DESTDIR)/usr/bin/smart-applet
	ln -sf /usr/bin/consolehelper $(DESTDIR)/usr/bin/smart-helper
	install -d $(DESTDIR)/usr/share/pixmaps
	install -m 0644 smart-applet.png $(DESTDIR)/usr/share/pixmaps
	install -d $(DESTDIR)/etc/pam.d
	install -m 0644 smart-helper.pam $(DESTDIR)/etc/pam.d/smart-helper
	install -d $(DESTDIR)/etc/security/console.apps
	install -m 0644 smart-helper.helper $(DESTDIR)/etc/security/console.apps/smart-helper

uninstall:
	rm -f $(DESTDIR)/usr/bin/smart-applet
	rm -f $(DESTDIR)/usr/bin/smart-helper
	rm -f $(DESTDIR)/etc/pam.d/smart-helper
	rm -f $(DESTDIR)/etc/security/console.apps/smart-helper
