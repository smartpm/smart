from gepeto.commands import query

HELP="""
Usage: gpt search expression ...

This command allows searching for the given expressions
in the name, summary, and description of known packages.

Options:
  -h, --help  Show this help message and exit

Examples:
  gpt search ldap
  gpt search kernel module
  gpt search rpm 'package manager'
  gpt search pkgname
  gpt search 'pkgn*e'
"""

def parse_options(argv):
    opts = query.parse_options(argv, help=HELP)
    opts.name = opts.args
    opts.summary = opts.args
    opts.description = opts.args
    opts.show_summary = True
    opts.hide_version = True
    opts.args = []
    return opts

main = query.main
