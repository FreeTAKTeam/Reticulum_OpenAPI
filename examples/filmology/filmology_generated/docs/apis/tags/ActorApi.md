<a id="__pageTop"></a>
# examples.filmology.apis.tags.actor_api.ActorApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_actor**](#create_actor) | **post** /Actor | Creates a new Actor record.
[**delete_actor**](#delete_actor) | **delete** /Actor | Deletes an existing Actor record based on the provided ID.
[**list_actor**](#list_actor) | **get** /Actor | Retrieves a list of all Actor
[**patch_actor**](#patch_actor) | **patch** /Actor | Updates an existing Actor record.
[**retreive_actor**](#retreive_actor) | **get** /Actor/{id} | retrieve an existing Actor record based on the provided ID.

# **create_actor**
<a id="create_actor"></a>
> Actor create_actor(actor)

Creates a new Actor record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import actor_api
from examples.filmology.model.actor import Actor
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = actor_api.ActorApi(api_client)

    # example passing only required values which don't have defaults set
    body = Actor(None)
    try:
        # Creates a new Actor record.
        api_response = api_instance.create_actor(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling ActorApi->create_actor: %s\n" % e)
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
[**Actor**](../../models/Actor.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#create_actor.ApiResponseFor200) | Success

#### create_actor.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Actor**](../../models/Actor.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **delete_actor**
<a id="delete_actor"></a>
> Actor delete_actor(id)

Deletes an existing Actor record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import actor_api
from examples.filmology.model.actor import Actor
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = actor_api.ActorApi(api_client)

    # example passing only required values which don't have defaults set
    query_params = {
        'id': "id_example",
    }
    try:
        # Deletes an existing Actor record based on the provided ID.
        api_response = api_instance.delete_actor(
            query_params=query_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling ActorApi->delete_actor: %s\n" % e)
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
200 | [ApiResponseFor200](#delete_actor.ApiResponseFor200) | Success

#### delete_actor.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Actor**](../../models/Actor.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **list_actor**
<a id="list_actor"></a>
> Actor list_actor()

Retrieves a list of all Actor

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import actor_api
from examples.filmology.model.actor import Actor
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = actor_api.ActorApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Retrieves a list of all Actor
        api_response = api_instance.list_actor()
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling ActorApi->list_actor: %s\n" % e)
```
### Parameters
This endpoint does not need any parameter.

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#list_actor.ApiResponseFor200) | Success

#### list_actor.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Actor**](../../models/Actor.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **patch_actor**
<a id="patch_actor"></a>
> Actor patch_actor(actor)

Updates an existing Actor record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import actor_api
from examples.filmology.model.actor import Actor
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = actor_api.ActorApi(api_client)

    # example passing only required values which don't have defaults set
    body = Actor(None)
    try:
        # Updates an existing Actor record.
        api_response = api_instance.patch_actor(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling ActorApi->patch_actor: %s\n" % e)
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
[**Actor**](../../models/Actor.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#patch_actor.ApiResponseFor200) | Success

#### patch_actor.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Actor**](../../models/Actor.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **retreive_actor**
<a id="retreive_actor"></a>
> Actor retreive_actor(id)

retrieve an existing Actor record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import actor_api
from examples.filmology.model.actor import Actor
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = actor_api.ActorApi(api_client)

    # example passing only required values which don't have defaults set
    path_params = {
        'id': "id_example",
    }
    try:
        # retrieve an existing Actor record based on the provided ID.
        api_response = api_instance.retreive_actor(
            path_params=path_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling ActorApi->retreive_actor: %s\n" % e)
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
200 | [ApiResponseFor200](#retreive_actor.ApiResponseFor200) | Success

#### retreive_actor.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Actor**](../../models/Actor.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

