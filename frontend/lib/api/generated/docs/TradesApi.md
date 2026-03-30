# TradesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1TradesReconcilePost**](#apiv1tradesreconcilepost) | **POST** /api/v1/trades/reconcile | Trigger manual broker reconciliation for closed trades|

# **apiV1TradesReconcilePost**
> APIResponse apiV1TradesReconcilePost()


### Example

```typescript
import {
    TradesApi,
    Configuration,
    ApiV1TradesReconcilePostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TradesApi(configuration);

let apiV1TradesReconcilePostRequest: ApiV1TradesReconcilePostRequest; // (optional)

const { status, data } = await apiInstance.apiV1TradesReconcilePost(
    apiV1TradesReconcilePostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1TradesReconcilePostRequest** | **ApiV1TradesReconcilePostRequest**|  | |


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Reconciliation job triggered |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

