from examples.filmology.paths.poster.get import ApiForget
from examples.filmology.paths.poster.post import ApiForpost
from examples.filmology.paths.poster.delete import ApiFordelete
from examples.filmology.paths.poster.patch import ApiForpatch


class Poster(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
