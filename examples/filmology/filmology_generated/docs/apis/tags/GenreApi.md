<a id="__pageTop"></a>
# examples.filmology.apis.tags.genre_api.GenreApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_genre**](#create_genre) | **post** /Genre | Creates a new Genre record.
[**delete_genre**](#delete_genre) | **delete** /Genre | Deletes an existing Genre record based on the provided ID.
[**list_genre**](#list_genre) | **get** /Genre | Retrieves a list of all Genre
[**patch_genre**](#patch_genre) | **patch** /Genre | Updates an existing Genre record.
[**retreive_genre**](#retreive_genre) | **get** /Genre/{id} | retrieve an existing Genre record based on the provided ID.

# **create_genre**
<a id="create_genre"></a>
> Genre create_genre(genre)

Creates a new Genre record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import genre_api
from examples.filmology.model.genre import Genre
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = genre_api.GenreApi(api_client)

    # example passing only required values which don't have defaults set
    body = Genre(None)
    try:
        # Creates a new Genre record.
        api_response = api_instance.create_genre(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling GenreApi->create_genre: %s\n" % e)
```
### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
body | typing.Union[SchemaForRequestBodyApplicationJson] | required |
content_type | str | optional, default is 'application/json' | Selects the schema and serialization of the request body
accept_content_types | typing.Tuple[str] | default is ('application/json', ) | Tells the server the content type(s) that are accepted by the client
stream | bool | default is False | if True then the response.content will be streamed and loaded from a file like object. When downloading a file, set this to True to force the code to deserialize the content to a FileSchema file
timeout | typing.Optional[typing.Union[int, typing.Tuple]] | default is None | the timeout used by the rest client
skip_deserialization | bool | default is False | when True, headers and body will be unset and an instance of api_client.ApiResponseWithoutDeserialization will be returned

### body

# SchemaForRequestBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#create_genre.ApiResponseFor200) | Success

#### create_genre.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **delete_genre**
<a id="delete_genre"></a>
> Genre delete_genre(id)

Deletes an existing Genre record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import genre_api
from examples.filmology.model.genre import Genre
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = genre_api.GenreApi(api_client)

    # example passing only required values which don't have defaults set
    query_params = {
        'id': "id_example",
    }
    try:
        # Deletes an existing Genre record based on the provided ID.
        api_response = api_instance.delete_genre(
            query_params=query_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling GenreApi->delete_genre: %s\n" % e)
```
### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
query_params | RequestQueryParams | |
accept_content_types | typing.Tuple[str] | default is ('application/json', ) | Tells the server the content type(s) that are accepted by the client
stream | bool | default is False | if True then the response.content will be streamed and loaded from a file like object. When downloading a file, set this to True to force the code to deserialize the content to a FileSchema file
timeout | typing.Optional[typing.Union[int, typing.Tuple]] | default is None | the timeout used by the rest client
skip_deserialization | bool | default is False | when True, headers and body will be unset and an instance of api_client.ApiResponseWithoutDeserialization will be returned

### query_params
#### RequestQueryParams

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
id | IdSchema | | 


# IdSchema

## Model Type Info
Input Type | Accessed Type | Description | Notes
------------ | ------------- | ------------- | -------------
str,  | str,  |  | 

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#delete_genre.ApiResponseFor200) | Success

#### delete_genre.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **list_genre**
<a id="list_genre"></a>
> Genre list_genre()

Retrieves a list of all Genre

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import genre_api
from examples.filmology.model.genre import Genre
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = genre_api.GenreApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Retrieves a list of all Genre
        api_response = api_instance.list_genre()
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling GenreApi->list_genre: %s\n" % e)
```
### Parameters
This endpoint does not need any parameter.

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#list_genre.ApiResponseFor200) | Success

#### list_genre.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **patch_genre**
<a id="patch_genre"></a>
> Genre patch_genre(genre)

Updates an existing Genre record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import genre_api
from examples.filmology.model.genre import Genre
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = genre_api.GenreApi(api_client)

    # example passing only required values which don't have defaults set
    body = Genre(None)
    try:
        # Updates an existing Genre record.
        api_response = api_instance.patch_genre(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling GenreApi->patch_genre: %s\n" % e)
```
### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
body | typing.Union[SchemaForRequestBodyApplicationJson] | required |
content_type | str | optional, default is 'application/json' | Selects the schema and serialization of the request body
accept_content_types | typing.Tuple[str] | default is ('application/json', ) | Tells the server the content type(s) that are accepted by the client
stream | bool | default is False | if True then the response.content will be streamed and loaded from a file like object. When downloading a file, set this to True to force the code to deserialize the content to a FileSchema file
timeout | typing.Optional[typing.Union[int, typing.Tuple]] | default is None | the timeout used by the rest client
skip_deserialization | bool | default is False | when True, headers and body will be unset and an instance of api_client.ApiResponseWithoutDeserialization will be returned

### body

# SchemaForRequestBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#patch_genre.ApiResponseFor200) | Success

#### patch_genre.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **retreive_genre**
<a id="retreive_genre"></a>
> Genre retreive_genre(id)

retrieve an existing Genre record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import genre_api
from examples.filmology.model.genre import Genre
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = genre_api.GenreApi(api_client)

    # example passing only required values which don't have defaults set
    path_params = {
        'id': "id_example",
    }
    try:
        # retrieve an existing Genre record based on the provided ID.
        api_response = api_instance.retreive_genre(
            path_params=path_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling GenreApi->retreive_genre: %s\n" % e)
```
### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
path_params | RequestPathParams | |
accept_content_types | typing.Tuple[str] | default is ('application/json', ) | Tells the server the content type(s) that are accepted by the client
stream | bool | default is False | if True then the response.content will be streamed and loaded from a file like object. When downloading a file, set this to True to force the code to deserialize the content to a FileSchema file
timeout | typing.Optional[typing.Union[int, typing.Tuple]] | default is None | the timeout used by the rest client
skip_deserialization | bool | default is False | when True, headers and body will be unset and an instance of api_client.ApiResponseWithoutDeserialization will be returned

### path_params
#### RequestPathParams

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
id | IdSchema | | 

# IdSchema

## Model Type Info
Input Type | Accessed Type | Description | Notes
------------ | ------------- | ------------- | -------------
str,  | str,  |  | 

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#retreive_genre.ApiResponseFor200) | Success

#### retreive_genre.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Genre**](../../models/Genre.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

