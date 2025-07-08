from examples.filmology.paths.movie.get import ApiForget
from examples.filmology.paths.movie.post import ApiForpost
from examples.filmology.paths.movie.delete import ApiFordelete
from examples.filmology.paths.movie.patch import ApiForpatch


class Movie(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
