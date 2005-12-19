from smart import *
import sys
import os

TESTDATADIR = os.path.join(os.path.dirname(__file__), "data")
SMARTCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "smart.py")

def smart_process(*argv):
    import subprocess
    args = [SMARTCMD, "--data-dir", sysconf.get("data-dir")] + list(argv)
    process = subprocess.Popen(args, stderr=subprocess.STDOUT,
                               stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    return process
