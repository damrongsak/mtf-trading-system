# SystemApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiAdminQdrantHealthGet**](#apiv1aiadminqdranthealthget) | **GET** /api/v1/ai/admin/qdrant/health | Get Qdrant Health Status|
|[**apiV1SystemHaltPost**](#apiv1systemhaltpost) | **POST** /api/v1/system/halt | Emergency System Halt|
|[**apiV1SystemResumePost**](#apiv1systemresumepost) | **POST** /api/v1/system/resume | Emergency System Resume|

# **apiV1AiAdminQdrantHealthGet**
> APIResponse apiV1AiAdminQdrantHealthGet()

Detailed telemetry of Qdrant collections and system health.

### Example

```typescript
import {
    SystemApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SystemApi(configuration);

const { status, data } = await apiInstance.apiV1AiAdminQdrantHealthGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Health telemetry |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SystemHaltPost**
> APIResponse apiV1SystemHaltPost()

Sets the Global Kill Switch in Redis (system:kill_switch=1) to prevent all new trade executions.

### Example

```typescript
import {
    SystemApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SystemApi(configuration);

const { status, data } = await apiInstance.apiV1SystemHaltPost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | System Halted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SystemResumePost**
> APIResponse apiV1SystemResumePost()

Clears the Global Kill Switch in Redis to resume trade executions.

### Example

```typescript
import {
    SystemApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SystemApi(configuration);

const { status, data } = await apiInstance.apiV1SystemResumePost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | System Resumed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

