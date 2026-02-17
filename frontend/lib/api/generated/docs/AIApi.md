# AIApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiJournalAnalysisPost**](#apiv1aijournalanalysispost) | **POST** /api/v1/ai/journal-analysis | Analyze journal entry|
|[**apiV1AiMarketAnalysisPost**](#apiv1aimarketanalysispost) | **POST** /api/v1/ai/market-analysis | Generate market outlook|
|[**apiV1AiSmcNarrativePost**](#apiv1aismcnarrativepost) | **POST** /api/v1/ai/smc-narrative | Generate SMC Narrative|

# **apiV1AiJournalAnalysisPost**
> APIResponseAnalysis apiV1AiJournalAnalysisPost()


### Example

```typescript
import {
    AIApi,
    Configuration,
    JournalAnalysisRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let journalAnalysisRequest: JournalAnalysisRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiJournalAnalysisPost(
    journalAnalysisRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **journalAnalysisRequest** | **JournalAnalysisRequest**|  | |


### Return type

**APIResponseAnalysis**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Journal Analysis |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiMarketAnalysisPost**
> APIResponseAnalysis apiV1AiMarketAnalysisPost()


### Example

```typescript
import {
    AIApi,
    Configuration,
    MarketAnalysisRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let marketAnalysisRequest: MarketAnalysisRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiMarketAnalysisPost(
    marketAnalysisRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **marketAnalysisRequest** | **MarketAnalysisRequest**|  | |


### Return type

**APIResponseAnalysis**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Market Analysis |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiSmcNarrativePost**
> APIResponseAnalysis apiV1AiSmcNarrativePost()


### Example

```typescript
import {
    AIApi,
    Configuration,
    SMCNarrativeRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let sMCNarrativeRequest: SMCNarrativeRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiSmcNarrativePost(
    sMCNarrativeRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **sMCNarrativeRequest** | **SMCNarrativeRequest**|  | |


### Return type

**APIResponseAnalysis**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | SMC Narrative |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

