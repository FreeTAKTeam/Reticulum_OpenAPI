from examples.filmology.paths.genre.get import ApiForget
from examples.filmology.paths.genre.post import ApiForpost
from examples.filmology.paths.genre.delete import ApiFordelete
from examples.filmology.paths.genre.patch import ApiForpatch


class Genre(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
