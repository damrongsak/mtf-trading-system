# SignalApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1SignalsCancelAllPost**](#apiv1signalscancelallpost) | **POST** /api/v1/signals/cancel-all | Bulk cancel pending signals|

# **apiV1SignalsCancelAllPost**
> ApiV1SignalsCancelAllPost200Response apiV1SignalsCancelAllPost()

Reject all signals in PENDING_APPROVAL state.

### Example

```typescript
import {
    SignalApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new SignalApi(configuration);

let deploymentId: string; // (optional) (default to undefined)
let symbol: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1SignalsCancelAllPost(
    deploymentId,
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **deploymentId** | [**string**] |  | (optional) defaults to undefined|
| **symbol** | [**string**] |  | (optional) defaults to undefined|


### Return type

**ApiV1SignalsCancelAllPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Signals Cancelled |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

