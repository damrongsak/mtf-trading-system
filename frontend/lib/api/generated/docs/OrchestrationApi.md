# OrchestrationApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1OrchestrationCacheStatusGet**](#apiv1orchestrationcachestatusget) | **GET** /api/v1/orchestration/cache/status | Get semantic cache statistics|
|[**apiV1OrchestrationLogsGet**](#apiv1orchestrationlogsget) | **GET** /api/v1/orchestration/logs | Fetch latest agent orchestration logs|
|[**apiV1OrchestrationPipelineStatusGet**](#apiv1orchestrationpipelinestatusget) | **GET** /api/v1/orchestration/pipeline/status | Get status of autonomous pipelines|

# **apiV1OrchestrationCacheStatusGet**
> apiV1OrchestrationCacheStatusGet()


### Example

```typescript
import {
    OrchestrationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new OrchestrationApi(configuration);

const { status, data } = await apiInstance.apiV1OrchestrationCacheStatusGet();
```

### Parameters
This endpoint does not have any parameters.


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
|**200** | Cache stats |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1OrchestrationLogsGet**
> APIResponseOrchestrationLogs apiV1OrchestrationLogsGet()


### Example

```typescript
import {
    OrchestrationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new OrchestrationApi(configuration);

let limit: number; // (optional) (default to 50)

const { status, data } = await apiInstance.apiV1OrchestrationLogsGet(
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|


### Return type

**APIResponseOrchestrationLogs**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of audit logs |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1OrchestrationPipelineStatusGet**
> APIResponsePipelineStatus apiV1OrchestrationPipelineStatusGet()


### Example

```typescript
import {
    OrchestrationApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new OrchestrationApi(configuration);

const { status, data } = await apiInstance.apiV1OrchestrationPipelineStatusGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponsePipelineStatus**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Pipeline status |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

