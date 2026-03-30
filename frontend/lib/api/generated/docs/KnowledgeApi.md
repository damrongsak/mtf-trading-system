# KnowledgeApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1KnowledgeGraphDelete**](#apiv1knowledgegraphdelete) | **DELETE** /api/v1/knowledge/graph | Full reset of the knowledge graph|
|[**apiV1KnowledgeIngestBatchPost**](#apiv1knowledgeingestbatchpost) | **POST** /api/v1/knowledge/ingest/batch | Upload multiple files for knowledge ingestion|
|[**apiV1KnowledgeIngestDirectoryPost**](#apiv1knowledgeingestdirectorypost) | **POST** /api/v1/knowledge/ingest/directory | Trigger bulk ingestion from a local server directory|
|[**apiV1KnowledgeIngestPost**](#apiv1knowledgeingestpost) | **POST** /api/v1/knowledge/ingest | Upload a file for knowledge ingestion|
|[**apiV1KnowledgeIngestUrlPost**](#apiv1knowledgeingesturlpost) | **POST** /api/v1/knowledge/ingest/url | Provide a URL for knowledge ingestion|
|[**apiV1KnowledgeStatusTaskIdGet**](#apiv1knowledgestatustaskidget) | **GET** /api/v1/knowledge/status/{task_id} | Get the status of a specific ingestion task|
|[**apiV1KnowledgeTasksGet**](#apiv1knowledgetasksget) | **GET** /api/v1/knowledge/tasks | List all recent ingestion tasks|
|[**apiV1StreamLlmPost**](#apiv1streamllmpost) | **POST** /api/v1/stream/llm | Stream token-by-token LLM responses|
|[**apiV1StreamStatusTaskIdGet**](#apiv1streamstatustaskidget) | **GET** /api/v1/stream/status/{task_id} | Stream real-time pipeline progress events|

# **apiV1KnowledgeGraphDelete**
> APIResponse apiV1KnowledgeGraphDelete()

Deletes all nodes and relationships in FalkorDB.

### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

const { status, data } = await apiInstance.apiV1KnowledgeGraphDelete();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Graph deleted successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeIngestBatchPost**
> ApiV1KnowledgeIngestBatchPost202Response apiV1KnowledgeIngestBatchPost()


### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let files: Array<File>; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1KnowledgeIngestBatchPost(
    files
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **files** | **Array&lt;File&gt;** |  | (optional) defaults to undefined|


### Return type

**ApiV1KnowledgeIngestBatchPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Batch ingestion jobs accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeIngestDirectoryPost**
> ApiV1KnowledgeIngestDirectoryPost202Response apiV1KnowledgeIngestDirectoryPost(apiV1KnowledgeIngestDirectoryPostRequest)


### Example

```typescript
import {
    KnowledgeApi,
    Configuration,
    ApiV1KnowledgeIngestDirectoryPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let apiV1KnowledgeIngestDirectoryPostRequest: ApiV1KnowledgeIngestDirectoryPostRequest; //

const { status, data } = await apiInstance.apiV1KnowledgeIngestDirectoryPost(
    apiV1KnowledgeIngestDirectoryPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1KnowledgeIngestDirectoryPostRequest** | **ApiV1KnowledgeIngestDirectoryPostRequest**|  | |


### Return type

**ApiV1KnowledgeIngestDirectoryPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Directory ingestion job accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeIngestPost**
> ApiV1KnowledgeIngestPost202Response apiV1KnowledgeIngestPost()


### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let file: File; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1KnowledgeIngestPost(
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|


### Return type

**ApiV1KnowledgeIngestPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Ingestion job accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeIngestUrlPost**
> ApiV1KnowledgeIngestUrlPost202Response apiV1KnowledgeIngestUrlPost(apiV1KnowledgeIngestUrlPostRequest)


### Example

```typescript
import {
    KnowledgeApi,
    Configuration,
    ApiV1KnowledgeIngestUrlPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let apiV1KnowledgeIngestUrlPostRequest: ApiV1KnowledgeIngestUrlPostRequest; //

const { status, data } = await apiInstance.apiV1KnowledgeIngestUrlPost(
    apiV1KnowledgeIngestUrlPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1KnowledgeIngestUrlPostRequest** | **ApiV1KnowledgeIngestUrlPostRequest**|  | |


### Return type

**ApiV1KnowledgeIngestUrlPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | URL ingestion job accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeStatusTaskIdGet**
> ApiV1KnowledgeStatusTaskIdGet200Response apiV1KnowledgeStatusTaskIdGet()


### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1KnowledgeStatusTaskIdGet(
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1KnowledgeStatusTaskIdGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Task status details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1KnowledgeTasksGet**
> { [key: string]: object; } apiV1KnowledgeTasksGet()


### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

const { status, data } = await apiInstance.apiV1KnowledgeTasksGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**{ [key: string]: object; }**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of ingestion tasks |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StreamLlmPost**
> string apiV1StreamLlmPost(lLMStreamRequest)


### Example

```typescript
import {
    KnowledgeApi,
    Configuration,
    LLMStreamRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let lLMStreamRequest: LLMStreamRequest; //

const { status, data } = await apiInstance.apiV1StreamLlmPost(
    lLMStreamRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **lLMStreamRequest** | **LLMStreamRequest**|  | |


### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: text/event-stream


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | SSE stream of LLM tokens |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StreamStatusTaskIdGet**
> string apiV1StreamStatusTaskIdGet()


### Example

```typescript
import {
    KnowledgeApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new KnowledgeApi(configuration);

let taskId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1StreamStatusTaskIdGet(
    taskId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|


### Return type

**string**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: text/event-stream


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | SSE stream of progress events |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

