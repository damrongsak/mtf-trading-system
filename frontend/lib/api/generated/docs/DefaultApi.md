# DefaultApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AuthTokenPost**](#apiv1authtokenpost) | **POST** /api/v1/auth/token | Login to get access token|
|[**apiV1FundsGet**](#apiv1fundsget) | **GET** /api/v1/funds | List funds for current user|
|[**apiV1FundsPost**](#apiv1fundspost) | **POST** /api/v1/funds | Create a new fund|
|[**apiV1JournalEntryIdGet**](#apiv1journalentryidget) | **GET** /api/v1/journal/{entry_id} | Get journal entry details|
|[**apiV1JournalGet**](#apiv1journalget) | **GET** /api/v1/journal/ | List journal entries for current user|
|[**apiV1JournalPost**](#apiv1journalpost) | **POST** /api/v1/journal/ | Create a new journal entry|
|[**apiV1RiskCheckPost**](#apiv1riskcheckpost) | **POST** /api/v1/risk/check | Check if a trade execution is allowed based on risk rules|
|[**apiV1SignalCheckPost**](#apiv1signalcheckpost) | **POST** /api/v1/signal/check | Check if a signal is valid given current state|
|[**apiV1StrategiesGet**](#apiv1strategiesget) | **GET** /api/v1/strategies | List strategies for a fund|
|[**apiV1StrategiesPost**](#apiv1strategiespost) | **POST** /api/v1/strategies | Create a new strategy configuration|
|[**apiV1UsersMeGet**](#apiv1usersmeget) | **GET** /api/v1/users/me | Get current user details|

# **apiV1AuthTokenPost**
> Token apiV1AuthTokenPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let username: string; // (optional) (default to undefined)
let password: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AuthTokenPost(
    username,
    password
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **username** | [**string**] |  | (optional) defaults to undefined|
| **password** | [**string**] |  | (optional) defaults to undefined|


### Return type

**Token**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/x-www-form-urlencoded
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful login |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FundsGet**
> Array<Fund> apiV1FundsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1FundsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<Fund>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of funds |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FundsPost**
> Fund apiV1FundsPost(fundCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    FundCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundCreate: FundCreate; //

const { status, data } = await apiInstance.apiV1FundsPost(
    fundCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundCreate** | **FundCreate**|  | |


### Return type

**Fund**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Fund created |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1JournalEntryIdGet**
> JournalEntryResponse apiV1JournalEntryIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let entryId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1JournalEntryIdGet(
    entryId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **entryId** | [**string**] |  | defaults to undefined|


### Return type

**JournalEntryResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Journal entry details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1JournalGet**
> Array<JournalEntryResponse> apiV1JournalGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1JournalGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<JournalEntryResponse>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of journal entries |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1JournalPost**
> JournalEntryResponse apiV1JournalPost(journalEntryCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    JournalEntryCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let journalEntryCreate: JournalEntryCreate; //

const { status, data } = await apiInstance.apiV1JournalPost(
    journalEntryCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **journalEntryCreate** | **JournalEntryCreate**|  | |


### Return type

**JournalEntryResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Created journal entry |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1RiskCheckPost**
> RiskCheckResponse apiV1RiskCheckPost(riskCheckRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    RiskCheckRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let riskCheckRequest: RiskCheckRequest; //

const { status, data } = await apiInstance.apiV1RiskCheckPost(
    riskCheckRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **riskCheckRequest** | **RiskCheckRequest**|  | |


### Return type

**RiskCheckResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Risk check decision |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SignalCheckPost**
> SignalResponse apiV1SignalCheckPost(signalRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SignalRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let signalRequest: SignalRequest; //

const { status, data } = await apiInstance.apiV1SignalCheckPost(
    signalRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **signalRequest** | **SignalRequest**|  | |


### Return type

**SignalResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | signal check response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesGet**
> Array<Strategy> apiV1StrategiesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1StrategiesGet(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**Array<Strategy>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of strategies |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesPost**
> Strategy apiV1StrategiesPost(strategyCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    StrategyCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let strategyCreate: StrategyCreate; //

const { status, data } = await apiInstance.apiV1StrategiesPost(
    strategyCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **strategyCreate** | **StrategyCreate**|  | |


### Return type

**Strategy**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Strategy created |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1UsersMeGet**
> User apiV1UsersMeGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1UsersMeGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**User**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Current user |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

