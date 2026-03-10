# ExternalApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiExternalSearchPost**](#apiv1aiexternalsearchpost) | **POST** /api/v1/ai/external/search | External Search Access|
|[**apiV1ExternalWsCommandGet**](#apiv1externalwscommandget) | **GET** /api/v1/external/ws/command | WebSocket for High-Frequency Trading Commands|

# **apiV1AiExternalSearchPost**
> APIResponseLibraryResults apiV1AiExternalSearchPost()

Scoped search for 3rd-party consumers with limited metadata visibility.

### Example

```typescript
import {
    ExternalApi,
    Configuration,
    ExternalSearchRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExternalApi(configuration);

let externalSearchRequest: ExternalSearchRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiExternalSearchPost(
    externalSearchRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **externalSearchRequest** | **ExternalSearchRequest**|  | |


### Return type

**APIResponseLibraryResults**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Search results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExternalWsCommandGet**
> apiV1ExternalWsCommandGet()

Low-latency WebSocket connection for executing trading commands. Supports: execute, cancel, close, amend, get_orders, get_trades, get_account  **Authentication:** HMAC-SHA256 via query parameters (same as REST) **URL:** wss://{host}/api/v1/external/ws/command 

### Example

```typescript
import {
    ExternalApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExternalApi(configuration);

let apiKey: string; //Partner API Key (default to undefined)
let signature: string; //HMAC-SHA256 signature (default to undefined)
let timestamp: string; //Unix timestamp for signature (default to undefined)
let commands: string; //Comma-separated commands to subscribe (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1ExternalWsCommandGet(
    apiKey,
    signature,
    timestamp,
    commands
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiKey** | [**string**] | Partner API Key | defaults to undefined|
| **signature** | [**string**] | HMAC-SHA256 signature | defaults to undefined|
| **timestamp** | [**string**] | Unix timestamp for signature | defaults to undefined|
| **commands** | [**string**] | Comma-separated commands to subscribe | (optional) defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**101** | Switching Protocols to WebSocket |  -  |
|**401** | Unauthorized |  -  |
|**429** | Rate Limit Exceeded |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

