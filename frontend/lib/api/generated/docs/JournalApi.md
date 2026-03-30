# JournalApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1JournalPostMortemTradeIdGet**](#apiv1journalpostmortemtradeidget) | **GET** /api/v1/journal/post-mortem/{trade_id} | Get AI-generated post-mortem analysis for a trade|
|[**apiV1JournalPostMortemTradeIdPost**](#apiv1journalpostmortemtradeidpost) | **POST** /api/v1/journal/post-mortem/{trade_id} | Trigger generation of a new post-mortem analysis|

# **apiV1JournalPostMortemTradeIdGet**
> PostMortemResponse apiV1JournalPostMortemTradeIdGet()


### Example

```typescript
import {
    JournalApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new JournalApi(configuration);

let tradeId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1JournalPostMortemTradeIdGet(
    tradeId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tradeId** | [**string**] |  | defaults to undefined|


### Return type

**PostMortemResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Post-mortem analysis |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1JournalPostMortemTradeIdPost**
> AIJobAccepted apiV1JournalPostMortemTradeIdPost()


### Example

```typescript
import {
    JournalApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new JournalApi(configuration);

let tradeId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1JournalPostMortemTradeIdPost(
    tradeId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **tradeId** | [**string**] |  | defaults to undefined|


### Return type

**AIJobAccepted**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Analysis job accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

