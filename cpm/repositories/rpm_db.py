from cpm.backends.rpm.header import RPMDBLoader
from cpm.repository import Repository

class RPMDBRepository(Repository):

    def fetch(self, fetcher):
        self._loader = RPMDBLoader()
        self._loader.setRepository(self)

def create(type, data):
    if hasattr(data, "tag") and data.tag == "repository":
        node = data
        name = node.get("name")
        if not name:
            raise Error, "repository of type '%s' has no name" % type
        return RPMDBRepository(type, name)
    else:
        raise RepositoryDataError

# vim:ts=4:sw=4:et
