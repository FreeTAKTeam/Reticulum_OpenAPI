from examples.filmology.paths.director.get import ApiForget
from examples.filmology.paths.director.post import ApiForpost
from examples.filmology.paths.director.delete import ApiFordelete
from examples.filmology.paths.director.patch import ApiForpatch


class Director(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
