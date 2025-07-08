from examples.filmology.paths.date.get import ApiForget
from examples.filmology.paths.date.post import ApiForpost
from examples.filmology.paths.date.delete import ApiFordelete
from examples.filmology.paths.date.patch import ApiForpatch


class Date(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
