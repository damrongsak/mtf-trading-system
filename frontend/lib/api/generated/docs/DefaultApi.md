# DefaultApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AuthProfileGet**](#apiv1authprofileget) | **GET** /api/v1/auth/profile | Get current user profile|
|[**apiV1AuthRegisterPost**](#apiv1authregisterpost) | **POST** /api/v1/auth/register | Register a new user|
|[**apiV1AuthTokenPost**](#apiv1authtokenpost) | **POST** /api/v1/auth/token | Login to get access token|
|[**apiV1FundsGet**](#apiv1fundsget) | **GET** /api/v1/funds | List funds for current user|
|[**apiV1FundsPost**](#apiv1fundspost) | **POST** /api/v1/funds | Create a new fund|
|[**apiV1JournalEntryIdGet**](#apiv1journalentryidget) | **GET** /api/v1/journal/{entry_id} | Get journal entry details|
|[**apiV1JournalGet**](#apiv1journalget) | **GET** /api/v1/journal/ | List journal entries for current user|
|[**apiV1JournalPost**](#apiv1journalpost) | **POST** /api/v1/journal/ | Create a new journal entry|
|[**apiV1RiskCheckPost**](#apiv1riskcheckpost) | **POST** /api/v1/risk/check | Check if a trade execution is allowed based on risk rules|
|[**apiV1SignalCheckPost**](#apiv1signalcheckpost) | **POST** /api/v1/signal/check | Check if a signal is valid given current state|
|[**apiV1SignalLatestSymbolGet**](#apiv1signallatestsymbolget) | **GET** /api/v1/signal/latest/{symbol} | Get the latest signal for a specific symbol|
|[**apiV1StrategiesGet**](#apiv1strategiesget) | **GET** /api/v1/strategies | List strategies for a fund|
|[**apiV1StrategiesPost**](#apiv1strategiespost) | **POST** /api/v1/strategies | Create a new strategy configuration|
|[**apiV1TransactionsBalanceGet**](#apiv1transactionsbalanceget) | **GET** /api/v1/transactions/balance | Get fund balance|
|[**apiV1TransactionsGet**](#apiv1transactionsget) | **GET** /api/v1/transactions | List transactions|
|[**apiV1TransactionsImportPost**](#apiv1transactionsimportpost) | **POST** /api/v1/transactions/import | Import transactions from Excel|
|[**apiV1TransactionsPost**](#apiv1transactionspost) | **POST** /api/v1/transactions | Create a manual transaction|
|[**backtestResultsBacktestIdGet**](#backtestresultsbacktestidget) | **GET** /backtest/results/{backtest_id} | Get results of a specific backtest|
|[**backtestRunPost**](#backtestrunpost) | **POST** /backtest/run | Trigger a backtest|

# **apiV1AuthProfileGet**
> APIResponseUserResponse apiV1AuthProfileGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1AuthProfileGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseUserResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Current user profile |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AuthRegisterPost**
> APIResponseUserResponse apiV1AuthRegisterPost(userCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    UserCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let userCreate: UserCreate; //

const { status, data } = await apiInstance.apiV1AuthRegisterPost(
    userCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **userCreate** | **UserCreate**|  | |


### Return type

**APIResponseUserResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | User registered successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AuthTokenPost**
> APIResponseUserResponse apiV1AuthTokenPost()


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

**APIResponseUserResponse**

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
> PaginatedResponseFund apiV1FundsGet()


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

**PaginatedResponseFund**

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
> APIResponseFund apiV1FundsPost(fundCreate)


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

**APIResponseFund**

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
> APIResponseJournalEntryResponse apiV1JournalEntryIdGet()


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

**APIResponseJournalEntryResponse**

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
> PaginatedResponseJournalEntryResponse apiV1JournalGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let page: number; // (optional) (default to 1)
let perPage: number; // (optional) (default to 10)

const { status, data } = await apiInstance.apiV1JournalGet(
    page,
    perPage
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] |  | (optional) defaults to 1|
| **perPage** | [**number**] |  | (optional) defaults to 10|


### Return type

**PaginatedResponseJournalEntryResponse**

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
> APIResponseJournalEntryResponse apiV1JournalPost(journalEntryCreate)


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

**APIResponseJournalEntryResponse**

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
> APIResponseRiskCheckResponse apiV1RiskCheckPost(riskCheckRequest)


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

**APIResponseRiskCheckResponse**

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
> APIResponseSignalResponse apiV1SignalCheckPost(signalRequest)


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

**APIResponseSignalResponse**

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

# **apiV1SignalLatestSymbolGet**
> APIResponseSignalResponse apiV1SignalLatestSymbolGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let symbol: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1SignalLatestSymbolGet(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseSignalResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Latest signal |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesGet**
> PaginatedResponseStrategyResponse apiV1StrategiesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)
let page: number; // (optional) (default to 1)
let perPage: number; // (optional) (default to 10)

const { status, data } = await apiInstance.apiV1StrategiesGet(
    fundId,
    page,
    perPage
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|
| **page** | [**number**] |  | (optional) defaults to 1|
| **perPage** | [**number**] |  | (optional) defaults to 10|


### Return type

**PaginatedResponseStrategyResponse**

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
> APIResponseStrategyResponse apiV1StrategiesPost(strategyCreate)


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

**APIResponseStrategyResponse**

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

# **apiV1TransactionsBalanceGet**
> APIResponseBalanceResponse apiV1TransactionsBalanceGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1TransactionsBalanceGet(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseBalanceResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Current balance |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TransactionsGet**
> PaginatedResponseTransactionResponse apiV1TransactionsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)
let page: number; // (optional) (default to 1)
let perPage: number; // (optional) (default to 10)

const { status, data } = await apiInstance.apiV1TransactionsGet(
    fundId,
    page,
    perPage
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|
| **page** | [**number**] |  | (optional) defaults to 1|
| **perPage** | [**number**] |  | (optional) defaults to 10|


### Return type

**PaginatedResponseTransactionResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of transactions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TransactionsImportPost**
> APIResponseTransactionImportResponse apiV1TransactionsImportPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let file: File; // (optional) (default to undefined)
let fundId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1TransactionsImportPost(
    file,
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|
| **fundId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**APIResponseTransactionImportResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Import result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TransactionsPost**
> APIResponseTransactionResponse apiV1TransactionsPost(transactionCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    TransactionCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let transactionCreate: TransactionCreate; //

const { status, data } = await apiInstance.apiV1TransactionsPost(
    transactionCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **transactionCreate** | **TransactionCreate**|  | |


### Return type

**APIResponseTransactionResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Transaction created |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **backtestResultsBacktestIdGet**
> APIResponseBacktestResponse backtestResultsBacktestIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let backtestId: string; // (default to undefined)

const { status, data } = await apiInstance.backtestResultsBacktestIdGet(
    backtestId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **backtestId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseBacktestResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Backtest results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **backtestRunPost**
> APIResponseBacktestResponse backtestRunPost(backtestRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    BacktestRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let backtestRequest: BacktestRequest; //

const { status, data } = await apiInstance.backtestRunPost(
    backtestRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **backtestRequest** | **BacktestRequest**|  | |


### Return type

**APIResponseBacktestResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Backtest started/completed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

