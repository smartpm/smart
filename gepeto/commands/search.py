from gepeto.commands import query

def parse_options(argv):
    opts = query.parse_options(argv)
    opts.name = opts.args
    opts.summary = opts.args
    opts.description = opts.args
    opts.show_summary = True
    opts.hide_version = True
    opts.args = []
    return opts

main = query.main
