# DiagnosticApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet**](#apiv1executioninspectaccountaccountidsymbolsymbolget) | **GET** /api/v1/execution/inspect/account/{account_id}/symbol/{symbol} | Diagnostic endpoint for hierarchical execution normalization|

# **apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet**
> ApiV1ExecutionInspectAccountAccountIdSymbolSymbolGet200Response apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet()

Explains the internal-to-broker volume scaling and risk context (Zero-Math Standard).

### Example

```typescript
import {
    DiagnosticApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DiagnosticApi(configuration);

let accountId: string; // (default to undefined)
let symbol: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionInspectAccountAccountIdSymbolSymbolGet(
    accountId,
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **accountId** | [**string**] |  | defaults to undefined|
| **symbol** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1ExecutionInspectAccountAccountIdSymbolSymbolGet200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Hierarchical diagnostic output |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

