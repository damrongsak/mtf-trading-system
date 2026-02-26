# SystemApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1SystemQueueHealthGet**](#apiv1systemqueuehealthget) | **GET** /api/v1/system/queue-health | Get Async Execution Queue Health|

# **apiV1SystemQueueHealthGet**
> APIResponse apiV1SystemQueueHealthGet()

Returns the length (LLEN) of VIP, Retail, and Dead Letter Queues from Redis.

### Example

```typescript
import {
    SystemApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SystemApi(configuration);

const { status, data } = await apiInstance.apiV1SystemQueueHealthGet();
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
|**200** | Queue Health Data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

