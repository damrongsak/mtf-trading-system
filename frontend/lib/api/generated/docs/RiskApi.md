# RiskApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1FundsFundIdRiskParityGet**](#apiv1fundsfundidriskparityget) | **GET** /api/v1/funds/{fund_id}/risk-parity | Get real-time risk parity weights and sentiment for a fund|
|[**apiV1RiskAiReviewPost**](#apiv1riskaireviewpost) | **POST** /api/v1/risk/ai-review | Trigger AI-driven risk analysis for a fund|
|[**apiV1RiskFundFundIdApplyRecommendationPost**](#apiv1riskfundfundidapplyrecommendationpost) | **POST** /api/v1/risk/fund/{fund_id}/apply-recommendation | Apply AI risk recommendation to fund config|
|[**apiV1RiskFundFundIdConfigGet**](#apiv1riskfundfundidconfigget) | **GET** /api/v1/risk/fund/{fund_id}/config | Get fund-specific risk configuration|
|[**apiV1RiskFundFundIdConfigPatch**](#apiv1riskfundfundidconfigpatch) | **PATCH** /api/v1/risk/fund/{fund_id}/config | Update fund risk configuration|
|[**apiV1RiskFundFundIdKillSwitchPost**](#apiv1riskfundfundidkillswitchpost) | **POST** /api/v1/risk/fund/{fund_id}/kill-switch | Toggle fund-specific kill switch|
|[**apiV1RiskRebalanceHistoryGet**](#apiv1riskrebalancehistoryget) | **GET** /api/v1/risk/rebalance-history | Get rebalance history audit trail|

# **apiV1FundsFundIdRiskParityGet**
> APIResponseRiskParityData apiV1FundsFundIdRiskParityGet()


### Example

```typescript
import {
    RiskApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1FundsFundIdRiskParityGet(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseRiskParityData**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Risk parity data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskAiReviewPost**
> APIResponseRiskRecommendation apiV1RiskAiReviewPost(apiV1RiskAiReviewPostRequest)

Sends the fund\'s current risk configuration and market context to the AI Analyst\'s RiskRebalancerAgent (Gemini) for analysis. Returns a recommendation with suggested parameter adjustments. 

### Example

```typescript
import {
    RiskApi,
    Configuration,
    ApiV1RiskAiReviewPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let apiV1RiskAiReviewPostRequest: ApiV1RiskAiReviewPostRequest; //

const { status, data } = await apiInstance.apiV1RiskAiReviewPost(
    apiV1RiskAiReviewPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1RiskAiReviewPostRequest** | **ApiV1RiskAiReviewPostRequest**|  | |


### Return type

**APIResponseRiskRecommendation**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | AI risk recommendation |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskFundFundIdApplyRecommendationPost**
> APIResponseFundRiskConfig apiV1RiskFundFundIdApplyRecommendationPost(riskRecommendation)

Applies AI-suggested risk parameters (risk_percentage, max_drawdown_threshold) to the fund configuration and broadcasts a RISK_REBALANCE_APPLIED event to the Execution Service via Redis. 

### Example

```typescript
import {
    RiskApi,
    Configuration,
    RiskRecommendation
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (default to undefined)
let riskRecommendation: RiskRecommendation; //

const { status, data } = await apiInstance.apiV1RiskFundFundIdApplyRecommendationPost(
    fundId,
    riskRecommendation
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **riskRecommendation** | **RiskRecommendation**|  | |
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseFundRiskConfig**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Updated fund risk configuration |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskFundFundIdConfigGet**
> APIResponseFundRiskConfig apiV1RiskFundFundIdConfigGet()


### Example

```typescript
import {
    RiskApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1RiskFundFundIdConfigGet(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseFundRiskConfig**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Fund risk configuration |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskFundFundIdConfigPatch**
> APIResponseFundRiskConfig apiV1RiskFundFundIdConfigPatch(riskAdjustmentRequest)


### Example

```typescript
import {
    RiskApi,
    Configuration,
    RiskAdjustmentRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (default to undefined)
let riskAdjustmentRequest: RiskAdjustmentRequest; //

const { status, data } = await apiInstance.apiV1RiskFundFundIdConfigPatch(
    fundId,
    riskAdjustmentRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **riskAdjustmentRequest** | **RiskAdjustmentRequest**|  | |
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseFundRiskConfig**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Configuration updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskFundFundIdKillSwitchPost**
> APIResponse apiV1RiskFundFundIdKillSwitchPost(killSwitchRequest)


### Example

```typescript
import {
    RiskApi,
    Configuration,
    KillSwitchRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (default to undefined)
let killSwitchRequest: KillSwitchRequest; //

const { status, data } = await apiInstance.apiV1RiskFundFundIdKillSwitchPost(
    fundId,
    killSwitchRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **killSwitchRequest** | **KillSwitchRequest**|  | |
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Kill switch toggled |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskRebalanceHistoryGet**
> APIResponse apiV1RiskRebalanceHistoryGet()

Returns paginated list of AI risk rebalancing events for audit.

### Example

```typescript
import {
    RiskApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new RiskApi(configuration);

let fundId: string; // (optional) (default to undefined)
let limit: number; // (optional) (default to 20)

const { status, data } = await apiInstance.apiV1RiskRebalanceHistoryGet(
    fundId,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | (optional) defaults to undefined|
| **limit** | [**number**] |  | (optional) defaults to 20|


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
|**200** | Rebalance history list |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

