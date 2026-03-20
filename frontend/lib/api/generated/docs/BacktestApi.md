# BacktestApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**backtestMonteCarloPost**](#backtestmontecarlopost) | **POST** /backtest/monte-carlo | Run a Monte Carlo simulation|
|[**backtestOptimizePortfolioPost**](#backtestoptimizeportfoliopost) | **POST** /backtest/optimize/portfolio | Multi-strategy Portfolio Optimization|
|[**backtestWfaPost**](#backtestwfapost) | **POST** /backtest/wfa | Run Walk-Forward Analysis|

# **backtestMonteCarloPost**
> APIResponseMonteCarloResponse backtestMonteCarloPost(monteCarloRequest)


### Example

```typescript
import {
    BacktestApi,
    Configuration,
    MonteCarloRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new BacktestApi(configuration);

let monteCarloRequest: MonteCarloRequest; //

const { status, data } = await apiInstance.backtestMonteCarloPost(
    monteCarloRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **monteCarloRequest** | **MonteCarloRequest**|  | |


### Return type

**APIResponseMonteCarloResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Monte Carlo results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **backtestOptimizePortfolioPost**
> APIResponsePortfolioWeights backtestOptimizePortfolioPost(portfolioOptimizationRequest)


### Example

```typescript
import {
    BacktestApi,
    Configuration,
    PortfolioOptimizationRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new BacktestApi(configuration);

let portfolioOptimizationRequest: PortfolioOptimizationRequest; //

const { status, data } = await apiInstance.backtestOptimizePortfolioPost(
    portfolioOptimizationRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **portfolioOptimizationRequest** | **PortfolioOptimizationRequest**|  | |


### Return type

**APIResponsePortfolioWeights**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Optimal weights |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **backtestWfaPost**
> APIResponseWFAResponse backtestWfaPost(wFARequest)


### Example

```typescript
import {
    BacktestApi,
    Configuration,
    WFARequest
} from './api';

const configuration = new Configuration();
const apiInstance = new BacktestApi(configuration);

let wFARequest: WFARequest; //

const { status, data } = await apiInstance.backtestWfaPost(
    wFARequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **wFARequest** | **WFARequest**|  | |


### Return type

**APIResponseWFAResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | WFA results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

