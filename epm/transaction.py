
(
    REASON_INSTALL, 
    REASON_UPGRADE,
    REASON_CONFLICT,
    REASON_OBSOLETE,
) = range(1, 5)

class Transaction:
    def __init__(self):
        self.reason = {}
        self.obsolete = {}
        self.upgrade = {}
        self.install = {}
        self.remove = {}

# vim:ts=4:sw=4:et
