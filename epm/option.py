import optparse
import sys, os

__all__ = ["OptionParser"]

class CapitalizeHelpFormatter(optparse.IndentedHelpFormatter):

    def format_usage(self, usage):
        return optparse.IndentedHelpFormatter \
                .format_usage(self, usage).capitalize()

    def format_heading(self, heading):
        return optparse.IndentedHelpFormatter \
                .format_heading(self, heading).capitalize()

class OptionParser(optparse.OptionParser):

    def __init__(self, usage=None, help=None, **kwargs):
        if not "formatter" in kwargs:
            kwargs["formatter"] = CapitalizeHelpFormatter()
        optparse.OptionParser.__init__(self, usage, **kwargs)
        self._override_help = help

    def format_help(self, formatter=None):
        if self._override_help:
            return self._override_help
        else:
            return optparse.OptionParser.format_help(self, formatter)

# vim:et:ts=4:sw=4
