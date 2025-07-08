from reticulum_openapi.service import LXMFService
from examples.filmology.controllers import *
from model import *

class FilmologyManagementService(LXMFService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctrl_ActorApi = ActorApiController()
        self.add_route("", ctrl_ActorApi.)
        ctrl_DateApi = DateApiController()
        self.add_route("", ctrl_DateApi.)
        ctrl_DirectorApi = DirectorApiController()
        self.add_route("", ctrl_DirectorApi.)
        ctrl_GenreApi = GenreApiController()
        self.add_route("", ctrl_GenreApi.)
        ctrl_LanguageApi = LanguageApiController()
        self.add_route("", ctrl_LanguageApi.)
        ctrl_MovieApi = MovieApiController()
        self.add_route("", ctrl_MovieApi.)
        ctrl_PosterApi = PosterApiController()
        self.add_route("", ctrl_PosterApi.)
