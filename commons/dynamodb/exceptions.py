class RepositoryError(Exception):
    pass


class ObjectNotFoundError(RepositoryError):
    pass
