from cpm.backends.rpm.header import RPMDBLoader
from cpm.repository import Repository

class RPMDBRepository(Repository):

    def acquire(self, fetcher):
        self._loader = RPMDBLoader()

repository = RPMDBRepository

# vim:ts=4:sw=4:et
