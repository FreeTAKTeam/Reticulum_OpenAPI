# do not import all endpoints into this module because that uses a lot of memory and stack frames
# if you need the ability to import all endpoints from this module, import them with
# from examples.filmology.apis.tag_to_api import tag_to_api

import enum


class TagValues(str, enum.Enum):
    ACTOR = "Actor"
    DATE = "Date"
    DIRECTOR = "Director"
    GENRE = "Genre"
    LANGUAGE = "Language"
    MOVIE = "Movie"
    POSTER = "Poster"
