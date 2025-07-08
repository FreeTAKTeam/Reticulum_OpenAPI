from examples.filmology.paths.language.get import ApiForget
from examples.filmology.paths.language.post import ApiForpost
from examples.filmology.paths.language.delete import ApiFordelete
from examples.filmology.paths.language.patch import ApiForpatch


class Language(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
