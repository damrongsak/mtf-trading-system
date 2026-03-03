# AIApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiJournalAnalysisPost**](#apiv1aijournalanalysispost) | **POST** /api/v1/ai/journal-analysis | Analyze journal entry|
|[**apiV1AiLibraryIngestPost**](#apiv1ailibraryingestpost) | **POST** /api/v1/ai/library/ingest | Ingest a book into Quant Library|
|[**apiV1AiLibraryListGet**](#apiv1ailibrarylistget) | **GET** /api/v1/ai/library/list | List Library Books|
|[**apiV1AiLibraryStatusFilenameGet**](#apiv1ailibrarystatusfilenameget) | **GET** /api/v1/ai/library/status/{filename} | Get Library Ingestion Status|
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

# **apiV1AiLibraryIngestPost**
> APIResponseIngestionResult apiV1AiLibraryIngestPost()

Upload and semantically ingest a book (PDF/Markdown) into a Qdrant collection (defaults to quant_library).

### Example

```typescript
import {
    AIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let file: File; // (optional) (default to undefined)
let title: string; // (optional) (default to undefined)
let author: string; // (optional) (default to undefined)
let collection: string; //Qdrant collection name (e.g. trading_psychology) (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AiLibraryIngestPost(
    file,
    title,
    author,
    collection
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|
| **title** | [**string**] |  | (optional) defaults to undefined|
| **author** | [**string**] |  | (optional) defaults to undefined|
| **collection** | [**string**] | Qdrant collection name (e.g. trading_psychology) | (optional) defaults to undefined|


### Return type

**APIResponseIngestionResult**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Book ingestion started |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiLibraryListGet**
> APIResponseLibraryBookList apiV1AiLibraryListGet()

List all books in the library with their ingestion status.

### Example

```typescript
import {
    AIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

const { status, data } = await apiInstance.apiV1AiLibraryListGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseLibraryBookList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of books |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiLibraryStatusFilenameGet**
> APIResponseLibraryStatus apiV1AiLibraryStatusFilenameGet()

Check the status of a book ingestion by its filename.

### Example

```typescript
import {
    AIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let filename: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AiLibraryStatusFilenameGet(
    filename
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **filename** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseLibraryStatus**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Ingestion status |  -  |
|**404** | Book not found |  -  |

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

