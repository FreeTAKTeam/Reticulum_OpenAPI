from dataclasses import asdict

from reticulum_openapi.controller import Controller
from reticulum_openapi.controller import handle_exceptions

from .database import async_session
from .models_filmology import Movie


class MovieController(Controller):
    """Handlers for movie operations."""

    @handle_exceptions
    async def CreateMovie(self, req: dict):
        """Store a new movie.

        Args:
            req (dict): Incoming movie data.

        Returns:
            Movie: Persisted movie record.
        """
        movie = Movie(
            **{k: v for k, v in req.items() if k in Movie.__dataclass_fields__}
        )
        async with async_session() as session:
            await Movie.create(session, **asdict(movie))
        return movie

    @handle_exceptions
    async def RetrieveMovie(self, movie_id: int):
        """Fetch a movie by identifier.

        Args:
            movie_id (int): Movie identifier.

        Returns:
            Movie | None: Retrieved record or None.
        """
        async with async_session() as session:
            item = await Movie.get(session, movie_id)
        return item

    @handle_exceptions
    async def DeleteMovie(self, movie_id: int):
        """Remove a movie.

        Args:
            movie_id (int): Movie identifier.

        Returns:
            dict: Deletion status.
        """
        async with async_session() as session:
            deleted = await Movie.delete(session, movie_id)
        return {"status": "deleted" if deleted else "not_found", "id": movie_id}

    @handle_exceptions
    async def ListMovie(self):
        """List all movies.

        Returns:
            list[Movie]: Stored movies.
        """
        async with async_session() as session:
            items = await Movie.list(session)
        return items

    @handle_exceptions
    async def PatchMovie(self, req: dict):
        """Update an existing movie.

        Args:
            req (dict): Movie fields with existing id.

        Returns:
            Movie | None: Updated record or None if missing.
        """
        movie = Movie(
            **{k: v for k, v in req.items() if k in Movie.__dataclass_fields__}
        )
        async with async_session() as session:
            updated = await Movie.update(session, movie.id, **asdict(movie))
        return updated
