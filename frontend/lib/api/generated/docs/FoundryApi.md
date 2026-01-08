# FoundryApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**foundryAssemble**](#foundryassemble) | **POST** /api/v1/foundry/assemble | Assemble and Validate Strategy Config|
|[**foundryValidate**](#foundryvalidate) | **POST** /foundry/validate | Run Walk-Forward Validation|

# **foundryAssemble**
> APIResponseFoundryAssembleResponse foundryAssemble()


### Example

```typescript
import {
    FoundryApi,
    Configuration,
    FoundryAssembleRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new FoundryApi(configuration);

let foundryAssembleRequest: FoundryAssembleRequest; // (optional)

const { status, data } = await apiInstance.foundryAssemble(
    foundryAssembleRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **foundryAssembleRequest** | **FoundryAssembleRequest**|  | |


### Return type

**APIResponseFoundryAssembleResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful assembly |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **foundryValidate**
> APIResponseWalkForwardResponse foundryValidate()


### Example

```typescript
import {
    FoundryApi,
    Configuration,
    WalkForwardRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new FoundryApi(configuration);

let walkForwardRequest: WalkForwardRequest; // (optional)

const { status, data } = await apiInstance.foundryValidate(
    walkForwardRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **walkForwardRequest** | **WalkForwardRequest**|  | |


### Return type

**APIResponseWalkForwardResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful validation |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

