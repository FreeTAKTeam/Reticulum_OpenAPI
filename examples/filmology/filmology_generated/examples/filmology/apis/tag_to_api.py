import typing_extensions

from examples.filmology.apis.tags import TagValues
from examples.filmology.apis.tags.actor_api import ActorApi
from examples.filmology.apis.tags.date_api import DateApi
from examples.filmology.apis.tags.director_api import DirectorApi
from examples.filmology.apis.tags.genre_api import GenreApi
from examples.filmology.apis.tags.language_api import LanguageApi
from examples.filmology.apis.tags.movie_api import MovieApi
from examples.filmology.apis.tags.poster_api import PosterApi

TagToApi = typing_extensions.TypedDict(
    'TagToApi',
    {
        TagValues.ACTOR: ActorApi,
        TagValues.DATE: DateApi,
        TagValues.DIRECTOR: DirectorApi,
        TagValues.GENRE: GenreApi,
        TagValues.LANGUAGE: LanguageApi,
        TagValues.MOVIE: MovieApi,
        TagValues.POSTER: PosterApi,
    }
)

tag_to_api = TagToApi(
    {
        TagValues.ACTOR: ActorApi,
        TagValues.DATE: DateApi,
        TagValues.DIRECTOR: DirectorApi,
        TagValues.GENRE: GenreApi,
        TagValues.LANGUAGE: LanguageApi,
        TagValues.MOVIE: MovieApi,
        TagValues.POSTER: PosterApi,
    }
)
