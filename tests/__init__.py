from smart import *
import sys
import os
import doctest
import re

TESTDATADIR = os.path.join(os.path.dirname(__file__), "data")
SMARTCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "smart.py")

def smart_process(*argv):
    try:
        import subprocess
    except ImportError:
        # Python < 2.4
        subprocess = None
        import popen2
    args = [SMARTCMD,
            "--data-dir", sysconf.get("data-dir"),
            "-o", "detect-sys-channels=0",
            "-o", "channel-sync-dir=no-such-dir",
            "-o", "distro-init-file=None"
            ] + list(argv)
    if subprocess:
        process = subprocess.Popen(args, stderr=subprocess.STDOUT,
                                   stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    else:
        process = popen2.Popen4(args)
        process.stdout = process.fromchild
    return process

# Run list of examples, in context globs.  "out" can be used to display
# stuff to "the real" stdout, and fakeout is an instance of _SpoofOut
# that captures the examples' std output.  Return (#failures, #tries).
# NEW optionflags: DONT_ACCEPT_BLANKLINE, NORMALIZE_WHITESPACE, ELLIPSIS
def doctest_run_examples_inner(out, fakeout, examples, globs, verbose,
                               name, compileflags, optionflags):
    import sys, traceback
    OK, BOOM, FAIL = range(3)
    NADA = "nothing"
    stderr = doctest._SpoofOut()
    _tag_out = doctest._tag_out
    failures = 0
    for source, want, lineno in examples:
        if verbose:
            _tag_out(out, ("Trying", source),
                          ("Expecting", want or NADA))
        fakeout.clear()
        try:
            exec compile(source, "<string>", "single",
                         compileflags, 1) in globs
            got = fakeout.get()
            state = OK
        except KeyboardInterrupt:
            raise
        except:
            # See whether the exception was expected.
            if want.find("Traceback (innermost last):\n") == 0 or \
               want.find("Traceback (most recent call last):\n") == 0:
                # Only compare exception type and value - the rest of
                # the traceback isn't necessary.
                want = want.split('\n')[-2] + '\n'
                exc_type, exc_val = sys.exc_info()[:2]
                got = traceback.format_exception_only(exc_type, exc_val)[-1]
                state = OK
            else:
                # unexpected exception
                stderr.clear()
                traceback.print_exc(file=stderr)
                state = BOOM

        if state == OK:
            if _check_output(want, got, optionflags):
                if verbose:
                    out("ok\n")
                continue
            state = FAIL

        assert state in (FAIL, BOOM)
        failures = failures + 1
        out("*" * 65 + "\n")
        _tag_out(out, ("Failure in example", source))
        out("from line #" + `lineno` + " of " + name + "\n")
        if state == FAIL:
            _tag_out(out, ("Expected", want or NADA), ("Got", got))
        else:
            assert state == BOOM
            _tag_out(out, ("Exception raised", stderr.get()))

    return failures, len(examples)

# Special string markers for use in `want` strings:
BLANKLINE_MARKER = '<BLANKLINE>'
ELLIPSIS_MARKER = '...'

def _check_output(want, got, optionflags):
    """
    Return True iff the actual output from an example (`got`)
    matches the expected output (`want`).  These strings are
    always considered to match if they are identical; but
    depending on what option flags the test runner is using,
    several non-exact match types are also possible.  See the
    documentation for `TestRunner` for more information about
    option flags.
    """
    # Handle the common case first, for efficiency:
    # if they're string-identical, always return true.
    if got == want:
        return True

    # The values True and False replaced 1 and 0 as the return
    # value for boolean comparisons in Python 2.3.
    if not (optionflags & doctest.DONT_ACCEPT_TRUE_FOR_1):
        if (got,want) == ("True\n", "1\n"):
            return True
        if (got,want) == ("False\n", "0\n"):
            return True

    # <BLANKLINE> can be used as a special sequence to signify a
    # blank line, unless the DONT_ACCEPT_BLANKLINE flag is used.
    if not (optionflags & doctest.DONT_ACCEPT_BLANKLINE):
        # Replace <BLANKLINE> in want with a blank line.
        want = re.sub('(?m)^%s\s*?$' % re.escape(BLANKLINE_MARKER),
                      '', want)
        # If a line in got contains only spaces, then remove the
        # spaces.
        got = re.sub('(?m)^\s*?$', '', got)
        if got == want:
            return True

    # This flag causes doctest to ignore any differences in the
    # contents of whitespace strings.  Note that this can be used
    # in conjunction with the ELLIPSIS flag.
    if optionflags & doctest.NORMALIZE_WHITESPACE:
        got = ' '.join(got.split())
        want = ' '.join(want.split())
        if got == want:
            return True

    # The ELLIPSIS flag says to let the sequence "..." in `want`
    # match any substring in `got`.
    if optionflags & doctest.ELLIPSIS:
        if _ellipsis_match(want, got):
            return True

    # We didn't find any match; return false.
    return False

# Worst-case linear-time ellipsis matching.
def _ellipsis_match(want, got):
    """
    Essentially the only subtle case:
    >>> _ellipsis_match('aa...aa', 'aaa')
    False
    """
    if ELLIPSIS_MARKER not in want:
        return want == got

    # Find "the real" strings.
    ws = want.split(ELLIPSIS_MARKER)
    assert len(ws) >= 2

    # Deal with exact matches possibly needed at one or both ends.
    startpos, endpos = 0, len(got)
    w = ws[0]
    if w:   # starts with exact match
        if got.startswith(w):
            startpos = len(w)
            del ws[0]
        else:
            return False
    w = ws[-1]
    if w:   # ends with exact match
        if got.endswith(w):
            endpos -= len(w)
            del ws[-1]
        else:
            return False

    if startpos > endpos:
        # Exact end matches required more characters than we have, as in
        # _ellipsis_match('aa...aa', 'aaa')
        return False

    # For the rest, we only need to find the leftmost non-overlapping
    # match for each piece.  If there's no overall match that way alone,
    # there's no overall match period.
    for w in ws:
        # w may be '' at times, if there are consecutive ellipses, or
        # due to an ellipsis at the start or end of `want`.  That's OK.
        # Search for an empty string succeeds, and doesn't change startpos.
        startpos = got.find(w, startpos, endpos)
        if startpos < 0:
            return False
        startpos += len(w)

    return True
