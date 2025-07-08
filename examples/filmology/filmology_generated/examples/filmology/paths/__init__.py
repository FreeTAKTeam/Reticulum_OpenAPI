# do not import all endpoints into this module because that uses a lot of memory and stack frames
# if you need the ability to import all endpoints from this module, import them with
# from examples.filmology.apis.path_to_api import path_to_api

import enum


class PathValues(str, enum.Enum):
    MOVIE = "/Movie"
    DIRECTOR_ID = "/Director/{id}"
    POSTER = "/Poster"
    GENRE_ID = "/Genre/{id}"
    DATE = "/Date"
    LANGUAGE_ID = "/Language/{id}"
    DIRECTOR = "/Director"
    DATE_ID = "/Date/{id}"
    ACTOR = "/Actor"
    MOVIE_ID = "/Movie/{id}"
    LANGUAGE = "/Language"
    POSTER_ID = "/Poster/{id}"
    ACTOR_ID = "/Actor/{id}"
    GENRE = "/Genre"
