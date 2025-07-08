from examples.filmology.paths.actor.get import ApiForget
from examples.filmology.paths.actor.post import ApiForpost
from examples.filmology.paths.actor.delete import ApiFordelete
from examples.filmology.paths.actor.patch import ApiForpatch


class Actor(
    ApiForget,
    ApiForpost,
    ApiFordelete,
    ApiForpatch,
):
    pass
