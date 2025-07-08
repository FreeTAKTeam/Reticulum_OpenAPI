<a id="__pageTop"></a>
# examples.filmology.apis.tags.poster_api.PosterApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_poster**](#create_poster) | **post** /Poster | Creates a new Poster record.
[**delete_poster**](#delete_poster) | **delete** /Poster | Deletes an existing Poster record based on the provided ID.
[**list_poster**](#list_poster) | **get** /Poster | Retrieves a list of all Poster
[**patch_poster**](#patch_poster) | **patch** /Poster | Updates an existing Poster record.
[**retreive_poster**](#retreive_poster) | **get** /Poster/{id} | retrieve an existing Poster record based on the provided ID.

# **create_poster**
<a id="create_poster"></a>
> Poster create_poster(poster)

Creates a new Poster record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import poster_api
from examples.filmology.model.poster import Poster
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = poster_api.PosterApi(api_client)

    # example passing only required values which don't have defaults set
    body = Poster(None)
    try:
        # Creates a new Poster record.
        api_response = api_instance.create_poster(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling PosterApi->create_poster: %s\n" % e)
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
[**Poster**](../../models/Poster.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#create_poster.ApiResponseFor200) | Success

#### create_poster.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Poster**](../../models/Poster.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **delete_poster**
<a id="delete_poster"></a>
> Poster delete_poster(id)

Deletes an existing Poster record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import poster_api
from examples.filmology.model.poster import Poster
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = poster_api.PosterApi(api_client)

    # example passing only required values which don't have defaults set
    query_params = {
        'id': "id_example",
    }
    try:
        # Deletes an existing Poster record based on the provided ID.
        api_response = api_instance.delete_poster(
            query_params=query_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling PosterApi->delete_poster: %s\n" % e)
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
200 | [ApiResponseFor200](#delete_poster.ApiResponseFor200) | Success

#### delete_poster.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Poster**](../../models/Poster.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **list_poster**
<a id="list_poster"></a>
> Poster list_poster()

Retrieves a list of all Poster

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import poster_api
from examples.filmology.model.poster import Poster
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = poster_api.PosterApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Retrieves a list of all Poster
        api_response = api_instance.list_poster()
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling PosterApi->list_poster: %s\n" % e)
```
### Parameters
This endpoint does not need any parameter.

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#list_poster.ApiResponseFor200) | Success

#### list_poster.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Poster**](../../models/Poster.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **patch_poster**
<a id="patch_poster"></a>
> Poster patch_poster(poster)

Updates an existing Poster record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import poster_api
from examples.filmology.model.poster import Poster
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = poster_api.PosterApi(api_client)

    # example passing only required values which don't have defaults set
    body = Poster(None)
    try:
        # Updates an existing Poster record.
        api_response = api_instance.patch_poster(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling PosterApi->patch_poster: %s\n" % e)
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
[**Poster**](../../models/Poster.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#patch_poster.ApiResponseFor200) | Success

#### patch_poster.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Poster**](../../models/Poster.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **retreive_poster**
<a id="retreive_poster"></a>
> Poster retreive_poster(id)

retrieve an existing Poster record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import poster_api
from examples.filmology.model.poster import Poster
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = poster_api.PosterApi(api_client)

    # example passing only required values which don't have defaults set
    path_params = {
        'id': "id_example",
    }
    try:
        # retrieve an existing Poster record based on the provided ID.
        api_response = api_instance.retreive_poster(
            path_params=path_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling PosterApi->retreive_poster: %s\n" % e)
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
200 | [ApiResponseFor200](#retreive_poster.ApiResponseFor200) | Success

#### retreive_poster.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Poster**](../../models/Poster.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

