# AlphaApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AlphaPreviewPost**](#apiv1alphapreviewpost) | **POST** /api/v1/alpha/preview | Run lightweight preview for alpha formula|
|[**apiV1AlphaTestPost**](#apiv1alphatestpost) | **POST** /api/v1/alpha/test | Run detailed backtest for alpha formula|

# **apiV1AlphaPreviewPost**
> APIResponseAlpha apiV1AlphaPreviewPost(alphaRequest)


### Example

```typescript
import {
    AlphaApi,
    Configuration,
    AlphaRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AlphaApi(configuration);

let alphaRequest: AlphaRequest; //

const { status, data } = await apiInstance.apiV1AlphaPreviewPost(
    alphaRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **alphaRequest** | **AlphaRequest**|  | |


### Return type

**APIResponseAlpha**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Alpha preview results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AlphaTestPost**
> APIResponseAlpha apiV1AlphaTestPost(alphaRequest)


### Example

```typescript
import {
    AlphaApi,
    Configuration,
    AlphaRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AlphaApi(configuration);

let alphaRequest: AlphaRequest; //

const { status, data } = await apiInstance.apiV1AlphaTestPost(
    alphaRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **alphaRequest** | **AlphaRequest**|  | |


### Return type

**APIResponseAlpha**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Alpha backtest results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

