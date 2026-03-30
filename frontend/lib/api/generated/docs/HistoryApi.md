# HistoryApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1HistoryReconcilePost**](#apiv1historyreconcilepost) | **POST** /api/v1/history/reconcile | Trigger automated broker history reconciliation|

# **apiV1HistoryReconcilePost**
> APIResponse apiV1HistoryReconcilePost()


### Example

```typescript
import {
    HistoryApi,
    Configuration,
    ApiV1HistoryReconcilePostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new HistoryApi(configuration);

let apiV1HistoryReconcilePostRequest: ApiV1HistoryReconcilePostRequest; // (optional)

const { status, data } = await apiInstance.apiV1HistoryReconcilePost(
    apiV1HistoryReconcilePostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1HistoryReconcilePostRequest** | **ApiV1HistoryReconcilePostRequest**|  | |


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

