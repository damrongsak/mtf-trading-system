# NewsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1NewsCacheSymbolGet**](#apiv1newscachesymbolget) | **GET** /api/v1/news/cache/{symbol} | Get raw headlines from Redis cache|

# **apiV1NewsCacheSymbolGet**
> Array<ApiV1NewsCacheSymbolGet200ResponseInner> apiV1NewsCacheSymbolGet()

Returns the latest news headlines cached in Redis for a specific symbol. This is intended for 3rd party consumption.

### Example

```typescript
import {
    NewsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new NewsApi(configuration);

let symbol: string; // (default to 'XAUUSD')

const { status, data } = await apiInstance.apiV1NewsCacheSymbolGet(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to 'XAUUSD'|


### Return type

**Array<ApiV1NewsCacheSymbolGet200ResponseInner>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of cached headlines |  -  |
|**404** | No cached news found |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

