# DataApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1DataHistoryPitPost**](#apiv1datahistorypitpost) | **POST** /api/v1/data/history/pit | Point-in-Time Historical Data Recall|
|[**apiV1DataTickSymbolGet**](#apiv1dataticksymbolget) | **GET** /api/v1/data/tick/{symbol} | Get latest tick data for a symbol|

# **apiV1DataHistoryPitPost**
> APIResponsePITRecall apiV1DataHistoryPitPost(pITRecallRequest)

Returns labelled historical candle data for a specific period.

### Example

```typescript
import {
    DataApi,
    Configuration,
    PITRecallRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DataApi(configuration);

let pITRecallRequest: PITRecallRequest; //

const { status, data } = await apiInstance.apiV1DataHistoryPitPost(
    pITRecallRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **pITRecallRequest** | **PITRecallRequest**|  | |


### Return type

**APIResponsePITRecall**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Historical candle data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataTickSymbolGet**
> APIResponse apiV1DataTickSymbolGet()

Returns the latest bid, ask, and timestamp from Redis L2 cache.

### Example

```typescript
import {
    DataApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DataApi(configuration);

let symbol: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1DataTickSymbolGet(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|


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
|**200** | Latest tick data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

