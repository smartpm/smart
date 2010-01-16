#
# Make file for various operations on Smart source code
#

DESTDIR=/
PYTHON?=python

prefix=/usr
bindir=$(prefix)/bin

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install \
		--root=$(DESTDIR) \
		--prefix=$(prefix) \
		--install-scripts=$(bindir)

dist:
	$(PYTHON) setup.py sdist

rpm:
	$(PYTHON) setup.py bdist_rpm

clean:
	rm -rf build
	find smart/ -name *.pyc -exec rm -f {} \;
	find smart/ -name *.so -exec rm -f {} \;
	find locale/ -name *.mo -exec rm -f {} \;

smart.pot:
	xgettext -o locale/smart.pot `find -name '*.c' -o -name '*.py'`

update-po: smart.pot
	for po in locale/*/LC_MESSAGES/smart.po; do \
		echo -e "Merge: $$po: \c"; \
		msgmerge -v -U $$po locale/smart.pot; \
	done

check-po:
	for po in locale/*/LC_MESSAGES/smart.po; do \
		echo -e "Check: $$po: \c"; \
		msgfmt -o /dev/null --statistics -v -c $$po; \
	done

test:
	$(PYTHON) setup.py build_ext -i
	LANG=C $(PYTHON) test $(TEST)

.PHONY: clean smart.pot update-po check-po test

