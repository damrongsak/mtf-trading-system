# AIApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AiJobsJobIdGet**](#apiv1aijobsjobidget) | **GET** /api/v1/ai/jobs/{job_id} | Poll API for AI Analyst results|
|[**apiV1AiLibraryIngestPost**](#apiv1ailibraryingestpost) | **POST** /api/v1/ai/library/ingest | Ingest a book into Quant Library|
|[**apiV1AiLibraryListGet**](#apiv1ailibrarylistget) | **GET** /api/v1/ai/library/list | List Library Books|
|[**apiV1AiLibraryStatusFilenameGet**](#apiv1ailibrarystatusfilenameget) | **GET** /api/v1/ai/library/status/{filename} | Get Library Ingestion Status|
|[**apiV1AiMriCoachingPost**](#apiv1aimricoachingpost) | **POST** /api/v1/ai/mri/coaching | Get psychological coaching based on journal RAG|
|[**apiV1AiThinkPost**](#apiv1aithinkpost) | **POST** /api/v1/ai/think | Unified AI Orchestrator|

# **apiV1AiJobsJobIdGet**
> AIJobStatus apiV1AiJobsJobIdGet()


### Example

```typescript
import {
    AIApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let jobId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AiJobsJobIdGet(
    jobId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **jobId** | [**string**] |  | defaults to undefined|


### Return type

**AIJobStatus**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Job Status and Result |  -  |
|**503** | Orchestrator Busy/Unavailable |  -  |

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

# **apiV1AiMriCoachingPost**
> CoachingResponse apiV1AiMriCoachingPost()


### Example

```typescript
import {
    AIApi,
    Configuration,
    CoachingRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let userId: string; // (optional) (default to undefined)
let coachingRequest: CoachingRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiMriCoachingPost(
    userId,
    coachingRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **coachingRequest** | **CoachingRequest**|  | |
| **userId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**CoachingResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | AI Coaching Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiThinkPost**
> AIJobAccepted apiV1AiThinkPost(aIThinkRequest)

Single entry point for all AI Analyst requests (Chat, Briefing, Market Analysis, Journal). Routes to specialized agents via Supervisor.

### Example

```typescript
import {
    AIApi,
    Configuration,
    AIThinkRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AIApi(configuration);

let aIThinkRequest: AIThinkRequest; //

const { status, data } = await apiInstance.apiV1AiThinkPost(
    aIThinkRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **aIThinkRequest** | **AIThinkRequest**|  | |


### Return type

**AIJobAccepted**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | AI Request Accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

