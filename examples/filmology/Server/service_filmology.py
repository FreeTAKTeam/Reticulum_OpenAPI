from reticulum_openapi.service import LXMFService

from .controllers_filmology import MovieController
from .models_filmology import movie_schema


class FilmologyService(LXMFService):
    """Service exposing filmology routes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        controller = MovieController()
        self.add_route(
            "CreateMovie", controller.CreateMovie, payload_schema=movie_schema
        )
        self.add_route("RetrieveMovie", controller.RetrieveMovie)
        self.add_route("DeleteMovie", controller.DeleteMovie)
        self.add_route("ListMovie", controller.ListMovie)
        self.add_route("PatchMovie", controller.PatchMovie, payload_schema=movie_schema)
