from cpm.option import OptionParser
from cpm.cmdline import initCmdLine
from cpm.repository import *
from cpm import *
import os

USAGE="cpm repos [options]"

def parse_options(argv):
    parser = OptionParser(usage=USAGE)
    parser.add_option("--add", action="store_true",
                      help="arguments are key=value pairs defining a "
                           "repository, or a filename/url pointing to "
                           "a repository description")
    parser.add_option("--del", action="store_true", dest="delete",
                      help="arguments are repository names to be removed")
    parser.add_option("--show", action="store_true",
                      help="show repositories with names given as arguments "
                           "or all repositories, if no argument was given")
    parser.add_option("--enable", action="store_true",
                      help="arguments are repository names to be enabled")
    parser.add_option("--disable", action="store_true",
                      help="arguments are repository names to be disabled")
    parser.add_option("--force", action="store_true",
                      help="execute without asking")
    opts, args = parser.parse_args(argv)
    opts.args = args
    return opts

def main(opts):
    ctrl = initCmdLine(opts)
    
    if opts.add:

        if len(opts.args) == 1:
            arg = opts.args[0]
            if os.path.isfile(arg):
                data = open(arg).read()
                replst = parseRepositoryDescription(data)
            elif ":/" in arg:
                succ, fail = ctrl.fetchFiles([arg], "repository description")
                if fail:
                    raise Error, "unable to fetch repository description: %s" \
                                 % fail[arg]
                data = open(succ[arg]).read()
                replst = parseRepositoryDescription(data)
                os.unlink(succ[arg])
            else:
                raise Error, "don't know what to do with: %s" % arg
        else:
            replst = []
            rep = {}
            for arg in opts.args:
                if "=" not in arg:
                    raise Error, "argument '%s' has no '='" % arg
                key, value = arg.split("=")
                rep[key.strip()] = value.strip()
            if "type" not in rep:
                raise Error, "repository has no type"
            if "name" not in rep:
                raise Error, "repository has no name"

            replst.append(rep)

        changed = False
        curreplst = sysconf.get("repositories", [], setdefault=True)
        for rep in replst:
            desc = createRepositoryDescription(rep)
            if not desc:
                continue
            if not opts.force:
                print
                print desc
                print
                res = raw_input("Include this repository (y/N)? ").strip()
            if opts.force or res and res[0].lower() == "y":
                try:
                    createRepository(rep.get("type"), rep)
                except Error, e:
                    print "error: invalid description: %s" % e
                else:
                    name = rep.get("name")
                    while [x for x in curreplst if x.get("name") == name]:
                        print "Repository name '%s' is already in use." % name
                        res = raw_input("Choose another one: ").strip()
                        if res:
                            name = res
                    rep["name"] = name
                    changed = True
                    curreplst.append(rep)

        if changed:
            ctrl.saveSysConf()

    elif opts.delete:

        replst = sysconf.get("repositories", [])

        changed = False
        for arg in opts.args:

            if [x for x in replst if x.get("name") == arg]:
                res = raw_input("Remove repository '%s' (y/N)? " % arg).strip()
                if res and res[0].lower() == "y":
                    changed = True
                    replst = [x for x in replst if x.get("name") != arg]

        if changed:
            sysconf.set("repositories", replst)
            ctrl.saveSysConf()

    elif opts.enable or opts.disable:

        changed = False

        replst = sysconf.get("repositories", [])

        for rep in replst:
            if rep.get("name") in opts.args:
                if opts.enable:
                    if "disabled" in rep:
                        del rep["disabled"]
                else:
                    rep["disabled"] = "yes"
                changed = True
        
        if changed:
            ctrl.saveSysConf()

    elif opts.show:

        replst = sysconf.get("repositories", [])
        if opts.args:
            replst = [x for x in replst if x.get("name") in opts.args]

        for rep in replst:
            desc = createRepositoryDescription(rep)
            if desc:
                print desc
            print

# vim:ts=4:sw=4:et
