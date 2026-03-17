# KnowledgeApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1KnowledgeIngestBatchPost**](#apiv1knowledgeingestbatchpost) | **POST** /api/v1/knowledge/ingest/batch | Upload multiple files for knowledge ingestion|
|[**apiV1KnowledgeIngestPost**](#apiv1knowledgeingestpost) | **POST** /api/v1/knowledge/ingest | Upload a file for knowledge ingestion|
|[**apiV1KnowledgeIngestUrlPost**](#apiv1knowledgeingesturlpost) | **POST** /api/v1/knowledge/ingest/url | Provide a URL for knowledge ingestion|
|[**apiV1KnowledgeStatusTaskIdGet**](#apiv1knowledgestatustaskidget) | **GET** /api/v1/knowledge/status/{task_id} | Get the status of a specific ingestion task|
|[**apiV1KnowledgeTasksGet**](#apiv1knowledgetasksget) | **GET** /api/v1/knowledge/tasks | List all recent ingestion tasks|

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

