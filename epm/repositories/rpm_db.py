from epm.loaders.rpm.header import RPMDBLoader
from epm.repository import Repository

class RPMDBRepository(Repository):

    def acquire(self, fetcher):
        self._loader = RPMDBLoader()

repository = RPMDBRepository

# vim:ts=4:sw=4:et
