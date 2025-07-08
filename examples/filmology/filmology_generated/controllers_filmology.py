from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class ActorApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class DateApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class DirectorApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class GenreApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class LanguageApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class MovieApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


from dataclasses import asdict
from reticulum_openapi.controller import Controller, handle_exceptions
from model import *
from examples.filmology.database import async_session


class PosterApiController(Controller):
    @handle_exceptions
    async def (self):
        self.logger.info(" called")
        async with async_session() as session:
            # TODO: implement persistence or other logic
            pass


