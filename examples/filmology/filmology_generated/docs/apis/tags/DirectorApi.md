<a id="__pageTop"></a>
# examples.filmology.apis.tags.director_api.DirectorApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_director**](#create_director) | **post** /Director | Creates a new Director record.
[**delete_director**](#delete_director) | **delete** /Director | Deletes an existing Director record based on the provided ID.
[**list_director**](#list_director) | **get** /Director | Retrieves a list of all Director
[**patch_director**](#patch_director) | **patch** /Director | Updates an existing Director record.
[**retreive_director**](#retreive_director) | **get** /Director/{id} | retrieve an existing Director record based on the provided ID.

# **create_director**
<a id="create_director"></a>
> Director create_director(director)

Creates a new Director record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import director_api
from examples.filmology.model.director import Director
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = director_api.DirectorApi(api_client)

    # example passing only required values which don't have defaults set
    body = Director(None)
    try:
        # Creates a new Director record.
        api_response = api_instance.create_director(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DirectorApi->create_director: %s\n" % e)
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
[**Director**](../../models/Director.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#create_director.ApiResponseFor200) | Success

#### create_director.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Director**](../../models/Director.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **delete_director**
<a id="delete_director"></a>
> Director delete_director(id)

Deletes an existing Director record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import director_api
from examples.filmology.model.director import Director
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = director_api.DirectorApi(api_client)

    # example passing only required values which don't have defaults set
    query_params = {
        'id': "id_example",
    }
    try:
        # Deletes an existing Director record based on the provided ID.
        api_response = api_instance.delete_director(
            query_params=query_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DirectorApi->delete_director: %s\n" % e)
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
200 | [ApiResponseFor200](#delete_director.ApiResponseFor200) | Success

#### delete_director.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Director**](../../models/Director.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **list_director**
<a id="list_director"></a>
> Director list_director()

Retrieves a list of all Director

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import director_api
from examples.filmology.model.director import Director
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = director_api.DirectorApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Retrieves a list of all Director
        api_response = api_instance.list_director()
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DirectorApi->list_director: %s\n" % e)
```
### Parameters
This endpoint does not need any parameter.

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#list_director.ApiResponseFor200) | Success

#### list_director.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Director**](../../models/Director.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **patch_director**
<a id="patch_director"></a>
> Director patch_director(director)

Updates an existing Director record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import director_api
from examples.filmology.model.director import Director
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = director_api.DirectorApi(api_client)

    # example passing only required values which don't have defaults set
    body = Director(None)
    try:
        # Updates an existing Director record.
        api_response = api_instance.patch_director(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DirectorApi->patch_director: %s\n" % e)
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
[**Director**](../../models/Director.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#patch_director.ApiResponseFor200) | Success

#### patch_director.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Director**](../../models/Director.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **retreive_director**
<a id="retreive_director"></a>
> Director retreive_director(id)

retrieve an existing Director record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import director_api
from examples.filmology.model.director import Director
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = director_api.DirectorApi(api_client)

    # example passing only required values which don't have defaults set
    path_params = {
        'id': "id_example",
    }
    try:
        # retrieve an existing Director record based on the provided ID.
        api_response = api_instance.retreive_director(
            path_params=path_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DirectorApi->retreive_director: %s\n" % e)
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
200 | [ApiResponseFor200](#retreive_director.ApiResponseFor200) | Success

#### retreive_director.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Director**](../../models/Director.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

