from cpm.backends.rpm.header import RPMDBLoader
from cpm.repository import Repository

class RPMDBRepository(Repository):

    def fetch(self, fetcher):
        self._loader = RPMDBLoader()
        self._loader.setRepository(self)

def create(reptype, data):
    name = None
    if type(data) is dict:
        name = data.get("name")
    elif hasattr(data, "tag") and data.tag == "repository":
        name = data.get("name")
    else:
        raise RepositoryDataError
    if not name:
        raise Error, "repository of type '%s' has no name" % reptype
    return RPMDBRepository(reptype, name)

# vim:ts=4:sw=4:et
