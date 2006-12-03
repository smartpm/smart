#!/bin/bash
# Simple build script.

make -f admin/Makefile.common cvs && ./configure && make
