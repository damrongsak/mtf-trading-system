# ExecutionApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet**](#apiv1executioninspectaccountaccountidsymbolsymbolget) | **GET** /api/v1/execution/inspect/account/{account_id}/symbol/{symbol} | Diagnostic endpoint for hierarchical execution normalization|
|[**apiV1ExecutionOrdersDelete**](#apiv1executionordersdelete) | **DELETE** /api/v1/execution/orders | Bulk cancel orders|
|[**apiV1ExecutionOrdersGet**](#apiv1executionordersget) | **GET** /api/v1/execution/orders | List pending orders for a broker account|
|[**apiV1ExecutionOrdersIdDelete**](#apiv1executionordersiddelete) | **DELETE** /api/v1/execution/orders/{id} | Cancel a pending order on broker|
|[**apiV1ExecutionOrdersOrderIdDelete**](#apiv1executionordersorderiddelete) | **DELETE** /api/v1/execution/orders/{order_id} | Cancel a specific order|
|[**apiV1ExecutionOrdersOrderIdPut**](#apiv1executionordersorderidput) | **PUT** /api/v1/execution/orders/{order_id} | Modify a pending order|
|[**apiV1ExecutionOrdersPost**](#apiv1executionorderspost) | **POST** /api/v1/execution/orders | Place a new order|
|[**apiV1ExecutionTradesCloseAllPost**](#apiv1executiontradescloseallpost) | **POST** /api/v1/execution/trades/close-all | Close all open trades for an account|
|[**apiV1ExecutionTradesOpenPost**](#apiv1executiontradesopenpost) | **POST** /api/v1/execution/trades/open | Get open trades directly from broker|
|[**apiV1ExecutionTradesSyncPost**](#apiv1executiontradessyncpost) | **POST** /api/v1/execution/trades/sync | Sync Trades from Broker|
|[**apiV1ExecutionTradesTradeIdAmendPost**](#apiv1executiontradestradeidamendpost) | **POST** /api/v1/execution/trades/{trade_id}/amend | Amend an open position (SL/TP)|
|[**apiV1ExecutionTradesTradeIdClosePost**](#apiv1executiontradestradeidclosepost) | **POST** /api/v1/execution/trades/{trade_id}/close | Manually close a trade|
|[**apiV1SignalsIdApprovePost**](#apiv1signalsidapprovepost) | **POST** /api/v1/signals/{id}/approve | Approve a pending signal|
|[**apiV1SignalsIdRejectPost**](#apiv1signalsidrejectpost) | **POST** /api/v1/signals/{id}/reject | Reject a pending signal|

# **apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet**
> ApiV1ExecutionInspectAccountAccountIdSymbolSymbolGet200Response apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet()

Explains the internal-to-broker volume scaling and risk context (Zero-Math Standard).

### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let accountId: string; // (default to undefined)
let symbol: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet(
    accountId,
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **accountId** | [**string**] |  | defaults to undefined|
| **symbol** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1ExecutionInspectAccountAccountIdSymbolSymbolGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Hierarchical diagnostic output |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionOrdersDelete**
> object apiV1ExecutionOrdersDelete()


### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let brokerAccountId: string; // (default to undefined)
let symbol: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionOrdersDelete(
    brokerAccountId,
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **brokerAccountId** | [**string**] |  | defaults to undefined|
| **symbol** | [**string**] |  | (optional) defaults to undefined|


### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Bulk cancel command processed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionOrdersGet**
> ApiV1ExecutionOrdersGet200Response apiV1ExecutionOrdersGet()


### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let brokerAccountId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionOrdersGet(
    brokerAccountId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **brokerAccountId** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1ExecutionOrdersGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of pending orders |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

# **apiV1ExecutionOrdersOrderIdDelete**
> APIResponse apiV1ExecutionOrdersOrderIdDelete()


### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let orderId: string; // (default to undefined)
let brokerAccountId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionOrdersOrderIdDelete(
    orderId,
    brokerAccountId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **orderId** | [**string**] |  | defaults to undefined|
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
|**200** | Order cancelled |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionOrdersOrderIdPut**
> APIResponse apiV1ExecutionOrdersOrderIdPut(apiV1ExecutionOrdersOrderIdPutRequest)


### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionOrdersOrderIdPutRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let orderId: string; // (default to undefined)
let apiV1ExecutionOrdersOrderIdPutRequest: ApiV1ExecutionOrdersOrderIdPutRequest; //

const { status, data } = await apiInstance.apiV1ExecutionOrdersOrderIdPut(
    orderId,
    apiV1ExecutionOrdersOrderIdPutRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionOrdersOrderIdPutRequest** | **ApiV1ExecutionOrdersOrderIdPutRequest**|  | |
| **orderId** | [**string**] |  | defaults to undefined|


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
|**200** | Order modified |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionOrdersPost**
> APIResponse apiV1ExecutionOrdersPost(body)


### Example

```typescript
import {
    ExecutionApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let body: object; //

const { status, data } = await apiInstance.apiV1ExecutionOrdersPost(
    body
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **body** | **object**|  | |


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
|**200** | Order placed |  -  |

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

# **apiV1ExecutionTradesTradeIdAmendPost**
> APIResponse apiV1ExecutionTradesTradeIdAmendPost(apiV1ExecutionTradesTradeIdAmendPostRequest)


### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionTradesTradeIdAmendPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let tradeId: string; // (default to undefined)
let apiV1ExecutionTradesTradeIdAmendPostRequest: ApiV1ExecutionTradesTradeIdAmendPostRequest; //

const { status, data } = await apiInstance.apiV1ExecutionTradesTradeIdAmendPost(
    tradeId,
    apiV1ExecutionTradesTradeIdAmendPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesTradeIdAmendPostRequest** | **ApiV1ExecutionTradesTradeIdAmendPostRequest**|  | |
| **tradeId** | [**string**] |  | defaults to undefined|


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
|**200** | Position amended |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesTradeIdClosePost**
> APIResponse apiV1ExecutionTradesTradeIdClosePost()


### Example

```typescript
import {
    ExecutionApi,
    Configuration,
    ApiV1ExecutionTradesTradeIdClosePostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExecutionApi(configuration);

let tradeId: string; // (default to undefined)
let apiV1ExecutionTradesTradeIdClosePostRequest: ApiV1ExecutionTradesTradeIdClosePostRequest; // (optional)

const { status, data } = await apiInstance.apiV1ExecutionTradesTradeIdClosePost(
    tradeId,
    apiV1ExecutionTradesTradeIdClosePostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesTradeIdClosePostRequest** | **ApiV1ExecutionTradesTradeIdClosePostRequest**|  | |
| **tradeId** | [**string**] |  | defaults to undefined|


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
|**200** | Trade closed successfully |  -  |

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

