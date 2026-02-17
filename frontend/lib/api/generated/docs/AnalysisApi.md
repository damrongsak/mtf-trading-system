# AnalysisApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**analysisDriftPost**](#analysisdriftpost) | **POST** /analysis/drift | Analyze System Drift|
|[**apiV1AnalysisCalculateAdxPost**](#apiv1analysiscalculateadxpost) | **POST** /api/v1/analysis/calculate/adx | Calculate ADX|
|[**apiV1AnalysisCalculateAtrPost**](#apiv1analysiscalculateatrpost) | **POST** /api/v1/analysis/calculate/atr | Calculate ATR|
|[**apiV1AnalysisCalculateEmaPost**](#apiv1analysiscalculateemapost) | **POST** /api/v1/analysis/calculate/ema | Calculate EMA|
|[**apiV1AnalysisCalculateMacdPost**](#apiv1analysiscalculatemacdpost) | **POST** /api/v1/analysis/calculate/macd | Calculate MACD|
|[**apiV1AnalysisCalculateRsiPost**](#apiv1analysiscalculatersipost) | **POST** /api/v1/analysis/calculate/rsi | Calculate RSI|
|[**apiV1AnalysisGammaLevelsGet**](#apiv1analysisgammalevelsget) | **GET** /api/v1/analysis/gamma/levels | Get Gamma Levels and Market Regime|
|[**apiV1AnalysisOiUnifiedProfileGet**](#apiv1analysisoiunifiedprofileget) | **GET** /api/v1/analysis/oi/unified-profile | Get Unified Open Interest Profile|

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

# **apiV1AnalysisCalculateAdxPost**
> AdxResponse apiV1AnalysisCalculateAdxPost()


### Example

```typescript
import {
    AnalysisApi,
    Configuration,
    AdxRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let adxRequest: AdxRequest; // (optional)

const { status, data } = await apiInstance.apiV1AnalysisCalculateAdxPost(
    adxRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **adxRequest** | **AdxRequest**|  | |


### Return type

**AdxResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | ADX Calculation Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisCalculateAtrPost**
> IndicatorResponse apiV1AnalysisCalculateAtrPost()


### Example

```typescript
import {
    AnalysisApi,
    Configuration,
    AtrRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let atrRequest: AtrRequest; // (optional)

const { status, data } = await apiInstance.apiV1AnalysisCalculateAtrPost(
    atrRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **atrRequest** | **AtrRequest**|  | |


### Return type

**IndicatorResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | ATR Calculation Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisCalculateEmaPost**
> IndicatorResponse apiV1AnalysisCalculateEmaPost()


### Example

```typescript
import {
    AnalysisApi,
    Configuration,
    EmaRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let emaRequest: EmaRequest; // (optional)

const { status, data } = await apiInstance.apiV1AnalysisCalculateEmaPost(
    emaRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **emaRequest** | **EmaRequest**|  | |


### Return type

**IndicatorResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | EMA Calculation Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisCalculateMacdPost**
> MacdResponse apiV1AnalysisCalculateMacdPost()


### Example

```typescript
import {
    AnalysisApi,
    Configuration,
    MacdRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let macdRequest: MacdRequest; // (optional)

const { status, data } = await apiInstance.apiV1AnalysisCalculateMacdPost(
    macdRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **macdRequest** | **MacdRequest**|  | |


### Return type

**MacdResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | MACD Calculation Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisCalculateRsiPost**
> IndicatorResponse apiV1AnalysisCalculateRsiPost()


### Example

```typescript
import {
    AnalysisApi,
    Configuration,
    RsiRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let rsiRequest: RsiRequest; // (optional)

const { status, data } = await apiInstance.apiV1AnalysisCalculateRsiPost(
    rsiRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **rsiRequest** | **RsiRequest**|  | |


### Return type

**IndicatorResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | RSI Calculation Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisGammaLevelsGet**
> APIResponse apiV1AnalysisGammaLevelsGet()

Returns key liquidity levels (Call/Put Walls, Flip) derived from Options Open Interest.

### Example

```typescript
import {
    AnalysisApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let symbol: string; // (optional) (default to 'XAUUSD')
let currentPrice: number; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AnalysisGammaLevelsGet(
    symbol,
    currentPrice
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | (optional) defaults to 'XAUUSD'|
| **currentPrice** | [**number**] |  | (optional) defaults to undefined|


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
|**200** | Gamma Analysis Data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisOiUnifiedProfileGet**
> APIResponseUnifiedOIProfile apiV1AnalysisOiUnifiedProfileGet()

Centralized endpoint for current positioning, gamma levels, and sentiment drift.

### Example

```typescript
import {
    AnalysisApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new AnalysisApi(configuration);

let symbol: string; // (optional) (default to 'XAUUSD')

const { status, data } = await apiInstance.apiV1AnalysisOiUnifiedProfileGet(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | (optional) defaults to 'XAUUSD'|


### Return type

**APIResponseUnifiedOIProfile**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Unified OI Profile |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

