from epm.packagemanager import PackageManager
from epm.transaction import OPER_INSTALL, OPER_REMOVE
from epm import *

class RPMPackageManager:
    def commit(self, trans):
        remove = []
        install = []
        upgrade = []
        oper = trans.getOperations()
        for pkg in oper:
            if op == OPER_INSTALL:
                pass
                # Check if it obsoletes any package being
                # removed.
            elif op == OPER_REMOVE
                pass
