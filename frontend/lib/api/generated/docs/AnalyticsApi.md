# AnalyticsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AnalyticsDrawdownGet**](#apiv1analyticsdrawdownget) | **GET** /api/v1/analytics/drawdown | Get drawdown metrics for a symbol|
|[**apiV1AnalyticsExecutionRejectionsGet**](#apiv1analyticsexecutionrejectionsget) | **GET** /api/v1/analytics/execution/rejections | Get execution rejection audit|
|[**apiV1AnalyticsFactorsGet**](#apiv1analyticsfactorsget) | **GET** /api/v1/analytics/factors | Get factor exposures for a symbol|
|[**apiV1AnalyticsLatencyHeatmapGet**](#apiv1analyticslatencyheatmapget) | **GET** /api/v1/analytics/latency/heatmap | Get execution latency heatmap|
|[**apiV1AnalyticsPerformanceComparisonGet**](#apiv1analyticsperformancecomparisonget) | **GET** /api/v1/analytics/performance/comparison | Compare Live vs Shadow performance|
|[**apiV1AnalyticsVarGet**](#apiv1analyticsvarget) | **GET** /api/v1/analytics/var | Get VaR/CVaR metrics for a symbol|
|[**apiV1AnalyticsVolatilityGet**](#apiv1analyticsvolatilityget) | **GET** /api/v1/analytics/volatility | Get volatility metrics for a symbol|

# **apiV1AnalyticsDrawdownGet**
> APIResponseDrawdownMetrics apiV1AnalyticsDrawdownGet()


### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

let symbol: string; // (default to undefined)
let timeframe: string; // (optional) (default to 'H1')
let limit: number; // (optional) (default to 500)

const { status, data } = await apiInstance.apiV1AnalyticsDrawdownGet(
    symbol,
    timeframe,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | (optional) defaults to 'H1'|
| **limit** | [**number**] |  | (optional) defaults to 500|


### Return type

**APIResponseDrawdownMetrics**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Drawdown metrics |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsExecutionRejectionsGet**
> APIResponseExecutionRejection apiV1AnalyticsExecutionRejectionsGet()

Summarizes signal rejections by reason and count.

### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

const { status, data } = await apiInstance.apiV1AnalyticsExecutionRejectionsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseExecutionRejection**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Rejection audit data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsFactorsGet**
> APIResponseFactorExposures apiV1AnalyticsFactorsGet()


### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

let symbol: string; // (default to undefined)
let timeframe: string; // (optional) (default to 'H1')
let limit: number; // (optional) (default to 500)

const { status, data } = await apiInstance.apiV1AnalyticsFactorsGet(
    symbol,
    timeframe,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | (optional) defaults to 'H1'|
| **limit** | [**number**] |  | (optional) defaults to 500|


### Return type

**APIResponseFactorExposures**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Factor exposures |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsLatencyHeatmapGet**
> APIResponseLatencyHeatmap apiV1AnalyticsLatencyHeatmapGet()

Returns aggregated latency data grouped by hour and symbol.

### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

const { status, data } = await apiInstance.apiV1AnalyticsLatencyHeatmapGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseLatencyHeatmap**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Latency heatmap data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsPerformanceComparisonGet**
> APIResponsePerformanceComparison apiV1AnalyticsPerformanceComparisonGet()

Compares P&L and latency for the same signal IDs across live and shadow trades.

### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

const { status, data } = await apiInstance.apiV1AnalyticsPerformanceComparisonGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponsePerformanceComparison**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Performance comparison data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsVarGet**
> APIResponseVaRMetrics apiV1AnalyticsVarGet()


### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

let symbol: string; // (default to undefined)
let timeframe: string; // (optional) (default to 'H1')
let limit: number; // (optional) (default to 500)

const { status, data } = await apiInstance.apiV1AnalyticsVarGet(
    symbol,
    timeframe,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | (optional) defaults to 'H1'|
| **limit** | [**number**] |  | (optional) defaults to 500|


### Return type

**APIResponseVaRMetrics**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | VaR/CVaR metrics |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalyticsVolatilityGet**
> APIResponseVolatilityMetrics apiV1AnalyticsVolatilityGet()


### Example

```typescript
import {
    AnalyticsApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalyticsApi(configuration);

let symbol: string; // (default to undefined)
let timeframe: string; // (optional) (default to 'H1')
let limit: number; // (optional) (default to 500)

const { status, data } = await apiInstance.apiV1AnalyticsVolatilityGet(
    symbol,
    timeframe,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | (optional) defaults to 'H1'|
| **limit** | [**number**] |  | (optional) defaults to 500|


### Return type

**APIResponseVolatilityMetrics**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Volatility metrics |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

