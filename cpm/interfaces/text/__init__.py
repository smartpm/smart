from cpm import Error

def create(interactive):
    if interactive:
        raise Error, "text interface has no interactive support yet"
    else:
        from cpm.interfaces.text.interface import TextInterface
        return TextInterface()

# vim:ts=4:sw=4:et

