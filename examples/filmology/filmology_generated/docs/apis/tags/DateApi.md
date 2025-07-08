<a id="__pageTop"></a>
# examples.filmology.apis.tags.date_api.DateApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_date**](#create_date) | **post** /Date | Creates a new Date record.
[**delete_date**](#delete_date) | **delete** /Date | Deletes an existing Date record based on the provided ID.
[**list_date**](#list_date) | **get** /Date | Retrieves a list of all Date
[**patch_date**](#patch_date) | **patch** /Date | Updates an existing Date record.
[**retreive_date**](#retreive_date) | **get** /Date/{id} | retrieve an existing Date record based on the provided ID.

# **create_date**
<a id="create_date"></a>
> Date create_date(date)

Creates a new Date record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import date_api
from examples.filmology.model.date import Date
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = date_api.DateApi(api_client)

    # example passing only required values which don't have defaults set
    body = Date(None)
    try:
        # Creates a new Date record.
        api_response = api_instance.create_date(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DateApi->create_date: %s\n" % e)
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
[**Date**](../../models/Date.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#create_date.ApiResponseFor200) | Success

#### create_date.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Date**](../../models/Date.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **delete_date**
<a id="delete_date"></a>
> Date delete_date(id)

Deletes an existing Date record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import date_api
from examples.filmology.model.date import Date
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = date_api.DateApi(api_client)

    # example passing only required values which don't have defaults set
    query_params = {
        'id': "id_example",
    }
    try:
        # Deletes an existing Date record based on the provided ID.
        api_response = api_instance.delete_date(
            query_params=query_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DateApi->delete_date: %s\n" % e)
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
200 | [ApiResponseFor200](#delete_date.ApiResponseFor200) | Success

#### delete_date.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Date**](../../models/Date.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **list_date**
<a id="list_date"></a>
> Date list_date()

Retrieves a list of all Date

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import date_api
from examples.filmology.model.date import Date
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = date_api.DateApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Retrieves a list of all Date
        api_response = api_instance.list_date()
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DateApi->list_date: %s\n" % e)
```
### Parameters
This endpoint does not need any parameter.

### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#list_date.ApiResponseFor200) | Success

#### list_date.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Date**](../../models/Date.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **patch_date**
<a id="patch_date"></a>
> Date patch_date(date)

Updates an existing Date record.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import date_api
from examples.filmology.model.date import Date
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = date_api.DateApi(api_client)

    # example passing only required values which don't have defaults set
    body = Date(None)
    try:
        # Updates an existing Date record.
        api_response = api_instance.patch_date(
            body=body,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DateApi->patch_date: %s\n" % e)
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
[**Date**](../../models/Date.md) |  | 


### Return Types, Responses

Code | Class | Description
------------- | ------------- | -------------
n/a | api_client.ApiResponseWithoutDeserialization | When skip_deserialization is True this response is returned
200 | [ApiResponseFor200](#patch_date.ApiResponseFor200) | Success

#### patch_date.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Date**](../../models/Date.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

# **retreive_date**
<a id="retreive_date"></a>
> Date retreive_date(id)

retrieve an existing Date record based on the provided ID.

### Example

```python
import examples.filmology
from examples.filmology.apis.tags import date_api
from examples.filmology.model.date import Date
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = examples.filmology.Configuration(
    host = "http://localhost"
)

# Enter a context with an instance of the API client
with examples.filmology.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = date_api.DateApi(api_client)

    # example passing only required values which don't have defaults set
    path_params = {
        'id': "id_example",
    }
    try:
        # retrieve an existing Date record based on the provided ID.
        api_response = api_instance.retreive_date(
            path_params=path_params,
        )
        pprint(api_response)
    except examples.filmology.ApiException as e:
        print("Exception when calling DateApi->retreive_date: %s\n" % e)
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
200 | [ApiResponseFor200](#retreive_date.ApiResponseFor200) | Success

#### retreive_date.ApiResponseFor200
Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
response | urllib3.HTTPResponse | Raw response |
body | typing.Union[SchemaFor200ResponseBodyApplicationJson, ] |  |
headers | Unset | headers were not defined |

# SchemaFor200ResponseBodyApplicationJson
Type | Description  | Notes
------------- | ------------- | -------------
[**Date**](../../models/Date.md) |  | 


### Authorization

No authorization required

[[Back to top]](#__pageTop) [[Back to API list]](../../../README.md#documentation-for-api-endpoints) [[Back to Model list]](../../../README.md#documentation-for-models) [[Back to README]](../../../README.md)

