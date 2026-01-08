# AnalysisApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**analysisDriftPost**](#analysisdriftpost) | **POST** /analysis/drift | Analyze System Drift|

# **analysisDriftPost**
> AnalysisDriftPost200Response analysisDriftPost()

Detects if strategy filters are rejecting an abnormal number of trades (Drift).

### Example

```typescript
import {
    AnalysisApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let windowHours: number; // (optional) (default to 24)

const { status, data } = await apiInstance.analysisDriftPost(
    windowHours
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **windowHours** | [**number**] |  | (optional) defaults to 24|


### Return type

**AnalysisDriftPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Drift Analysis Report |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

