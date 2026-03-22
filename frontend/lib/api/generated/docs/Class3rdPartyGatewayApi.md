# Class3rdPartyGatewayApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1ExternalMarketSnapshotSymbolGet**](#apiv1externalmarketsnapshotsymbolget) | **GET** /api/v1/external/market/snapshot/{symbol} | Get O(1) market snapshot (ECST)|
|[**apiV1ExternalStrategiesActiveGet**](#apiv1externalstrategiesactiveget) | **GET** /api/v1/external/strategies/active | Institutional access to active strategy fleet|
|[**apiV1ExternalStrategiesIdTickPost**](#apiv1externalstrategiesidtickpost) | **POST** /api/v1/external/strategies/{id}/tick | Institutional manual strategy trigger|
|[**apiV1ExternalTradeExecutePost**](#apiv1externaltradeexecutepost) | **POST** /api/v1/external/trade/execute | High-performance trade execution for partners|

# **apiV1ExternalMarketSnapshotSymbolGet**
> apiV1ExternalMarketSnapshotSymbolGet()


### Example

```typescript
import {
    Class3rdPartyGatewayApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new Class3rdPartyGatewayApi(configuration);

let symbol: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExternalMarketSnapshotSymbolGet(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|


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
|**200** | Market snapshot data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExternalStrategiesActiveGet**
> apiV1ExternalStrategiesActiveGet()


### Example

```typescript
import {
    Class3rdPartyGatewayApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new Class3rdPartyGatewayApi(configuration);

const { status, data } = await apiInstance.apiV1ExternalStrategiesActiveGet();
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
|**200** | Active fleet status |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExternalStrategiesIdTickPost**
> apiV1ExternalStrategiesIdTickPost()


### Example

```typescript
import {
    Class3rdPartyGatewayApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new Class3rdPartyGatewayApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExternalStrategiesIdTickPost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


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
|**200** | Tick successful |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExternalTradeExecutePost**
> apiV1ExternalTradeExecutePost(body)


### Example

```typescript
import {
    Class3rdPartyGatewayApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new Class3rdPartyGatewayApi(configuration);

let body: object; //

const { status, data } = await apiInstance.apiV1ExternalTradeExecutePost(
    body
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **body** | **object**|  | |


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Trade accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

