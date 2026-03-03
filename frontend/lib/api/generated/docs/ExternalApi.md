# ExternalApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiExternalSearchPost**](#apiv1aiexternalsearchpost) | **POST** /api/v1/ai/external/search | External Search Access|

# **apiV1AiExternalSearchPost**
> APIResponseLibraryResults apiV1AiExternalSearchPost()

Scoped search for 3rd-party consumers with limited metadata visibility.

### Example

```typescript
import {
    ExternalApi,
    Configuration,
    ExternalSearchRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new ExternalApi(configuration);

let externalSearchRequest: ExternalSearchRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiExternalSearchPost(
    externalSearchRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **externalSearchRequest** | **ExternalSearchRequest**|  | |


### Return type

**APIResponseLibraryResults**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Search results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

