# StrategiesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1StrategiesActiveGet**](#apiv1strategiesactiveget) | **GET** /api/v1/strategies/active | List all active strategy instances in the fleet|
|[**apiV1StrategiesGet**](#apiv1strategiesget) | **GET** /api/v1/strategies | List available strategy templates|
|[**apiV1StrategiesIdTickPost**](#apiv1strategiesidtickpost) | **POST** /api/v1/strategies/{id}/tick | Manually trigger a strategy logic evaluation|
|[**apiV1StrategiesReloadPost**](#apiv1strategiesreloadpost) | **POST** /api/v1/strategies/reload | Hot reload all strategy plugins from disk|

# **apiV1StrategiesActiveGet**
> ApiV1StrategiesActiveGet200Response apiV1StrategiesActiveGet()


### Example

```typescript
import {
    StrategiesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new StrategiesApi(configuration);

const { status, data } = await apiInstance.apiV1StrategiesActiveGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**ApiV1StrategiesActiveGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Active fleet status |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesGet**
> Array<StrategyTemplate> apiV1StrategiesGet()


### Example

```typescript
import {
    StrategiesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new StrategiesApi(configuration);

const { status, data } = await apiInstance.apiV1StrategiesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<StrategyTemplate>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of strategy templates |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesIdTickPost**
> apiV1StrategiesIdTickPost()


### Example

```typescript
import {
    StrategiesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new StrategiesApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1StrategiesIdTickPost(
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
|**200** | Tick result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesReloadPost**
> apiV1StrategiesReloadPost()


### Example

```typescript
import {
    StrategiesApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new StrategiesApi(configuration);

const { status, data } = await apiInstance.apiV1StrategiesReloadPost();
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
|**200** | Reload successful |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

