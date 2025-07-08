import typing_extensions

from examples.filmology.paths import PathValues
from examples.filmology.apis.paths.movie import Movie
from examples.filmology.apis.paths.director_id import DirectorId
from examples.filmology.apis.paths.poster import Poster
from examples.filmology.apis.paths.genre_id import GenreId
from examples.filmology.apis.paths.date import Date
from examples.filmology.apis.paths.language_id import LanguageId
from examples.filmology.apis.paths.director import Director
from examples.filmology.apis.paths.date_id import DateId
from examples.filmology.apis.paths.actor import Actor
from examples.filmology.apis.paths.movie_id import MovieId
from examples.filmology.apis.paths.language import Language
from examples.filmology.apis.paths.poster_id import PosterId
from examples.filmology.apis.paths.actor_id import ActorId
from examples.filmology.apis.paths.genre import Genre

PathToApi = typing_extensions.TypedDict(
    'PathToApi',
    {
        PathValues.MOVIE: Movie,
        PathValues.DIRECTOR_ID: DirectorId,
        PathValues.POSTER: Poster,
        PathValues.GENRE_ID: GenreId,
        PathValues.DATE: Date,
        PathValues.LANGUAGE_ID: LanguageId,
        PathValues.DIRECTOR: Director,
        PathValues.DATE_ID: DateId,
        PathValues.ACTOR: Actor,
        PathValues.MOVIE_ID: MovieId,
        PathValues.LANGUAGE: Language,
        PathValues.POSTER_ID: PosterId,
        PathValues.ACTOR_ID: ActorId,
        PathValues.GENRE: Genre,
    }
)

path_to_api = PathToApi(
    {
        PathValues.MOVIE: Movie,
        PathValues.DIRECTOR_ID: DirectorId,
        PathValues.POSTER: Poster,
        PathValues.GENRE_ID: GenreId,
        PathValues.DATE: Date,
        PathValues.LANGUAGE_ID: LanguageId,
        PathValues.DIRECTOR: Director,
        PathValues.DATE_ID: DateId,
        PathValues.ACTOR: Actor,
        PathValues.MOVIE_ID: MovieId,
        PathValues.LANGUAGE: Language,
        PathValues.POSTER_ID: PosterId,
        PathValues.ACTOR_ID: ActorId,
        PathValues.GENRE: Genre,
    }
)
