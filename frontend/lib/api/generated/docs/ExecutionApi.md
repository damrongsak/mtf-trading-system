# ExecutionApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1ExecutionOrdersIdDelete**](#apiv1executionordersiddelete) | **DELETE** /api/v1/execution/orders/{id} | Cancel a pending order on broker|
|[**apiV1ExecutionTradesCloseAllPost**](#apiv1executiontradescloseallpost) | **POST** /api/v1/execution/trades/close-all | Close all open trades for an account|
|[**apiV1ExecutionTradesOpenPost**](#apiv1executiontradesopenpost) | **POST** /api/v1/execution/trades/open | Get open trades directly from broker|
|[**apiV1ExecutionTradesSyncPost**](#apiv1executiontradessyncpost) | **POST** /api/v1/execution/trades/sync | Sync Trades from Broker|
|[**apiV1SignalsIdApprovePost**](#apiv1signalsidapprovepost) | **POST** /api/v1/signals/{id}/approve | Approve a pending signal|
|[**apiV1SignalsIdRejectPost**](#apiv1signalsidrejectpost) | **POST** /api/v1/signals/{id}/reject | Reject a pending signal|

# **apiV1ExecutionOrdersIdDelete**
> APIResponse apiV1ExecutionOrdersIdDelete()


### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let id: string; // (default to undefined)
let brokerAccountId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionOrdersIdDelete(
    id,
    brokerAccountId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|
| **brokerAccountId** | [**string**] |  | defaults to undefined|


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
|**200** | Order Cancelled |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesCloseAllPost**
> APIResponse apiV1ExecutionTradesCloseAllPost(apiV1ExecutionTradesCloseAllPostRequest)


### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionTradesCloseAllPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let apiV1ExecutionTradesCloseAllPostRequest: ApiV1ExecutionTradesCloseAllPostRequest; //

const { status, data } = await apiInstance.apiV1ExecutionTradesCloseAllPost(
    apiV1ExecutionTradesCloseAllPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesCloseAllPostRequest** | **ApiV1ExecutionTradesCloseAllPostRequest**|  | |


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
|**200** | Command Sent |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesOpenPost**
> APIResponseTradeList apiV1ExecutionTradesOpenPost(apiV1ExecutionTradesOpenPostRequest)


### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionTradesOpenPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let apiV1ExecutionTradesOpenPostRequest: ApiV1ExecutionTradesOpenPostRequest; //

const { status, data } = await apiInstance.apiV1ExecutionTradesOpenPost(
    apiV1ExecutionTradesOpenPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesOpenPostRequest** | **ApiV1ExecutionTradesOpenPostRequest**|  | |


### Return type

**APIResponseTradeList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of open trades |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesSyncPost**
> ApiV1ExecutionTradesSyncPost200Response apiV1ExecutionTradesSyncPost(apiV1ExecutionTradesSyncPostRequest)

Triggers a manual synchronization of trades (history) from the broker account to the local database.

### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionTradesSyncPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let apiV1ExecutionTradesSyncPostRequest: ApiV1ExecutionTradesSyncPostRequest; //

const { status, data } = await apiInstance.apiV1ExecutionTradesSyncPost(
    apiV1ExecutionTradesSyncPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesSyncPostRequest** | **ApiV1ExecutionTradesSyncPostRequest**|  | |


### Return type

**ApiV1ExecutionTradesSyncPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Trades synced successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SignalsIdApprovePost**
> ApiV1SignalsIdApprovePost200Response apiV1SignalsIdApprovePost()

Manually trigger execution for a signal in PENDING_APPROVAL state.

### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1SignalsIdApprovePost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1SignalsIdApprovePost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Signal approved and executed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SignalsIdRejectPost**
> ApiV1SignalsIdRejectPost200Response apiV1SignalsIdRejectPost()

Mark a PENDING_APPROVAL signal as REJECTED.

### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1SignalsIdRejectPost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1SignalsIdRejectPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Signal rejected |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

