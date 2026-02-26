# DefaultApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1AccountsAccountIdDelete**](#apiv1accountsaccountiddelete) | **DELETE** /api/v1/accounts/{account_id} | Delete a broker account|
|[**apiV1AccountsAccountIdPut**](#apiv1accountsaccountidput) | **PUT** /api/v1/accounts/{account_id} | Update a broker account|
|[**apiV1AccountsGet**](#apiv1accountsget) | **GET** /api/v1/accounts/ | List broker accounts|
|[**apiV1AccountsPost**](#apiv1accountspost) | **POST** /api/v1/accounts/ | Add a new broker account|
|[**apiV1AiAgentObserverRunPost**](#apiv1aiagentobserverrunpost) | **POST** /api/v1/ai/agent/observer/run | Run Market Observer Agent|
|[**apiV1AiAgentsGet**](#apiv1aiagentsget) | **GET** /api/v1/ai/agents | List available AI Agents|
|[**apiV1AiAgentsIdGet**](#apiv1aiagentsidget) | **GET** /api/v1/ai/agents/{id} | Get AI Agent details|
|[**apiV1AiBriefingGet**](#apiv1aibriefingget) | **GET** /api/v1/ai/briefing | Get latest daily briefing|
|[**apiV1AiBriefingPost**](#apiv1aibriefingpost) | **POST** /api/v1/ai/briefing | Trigger generation of a new briefing|
|[**apiV1AiChatSessionsGet**](#apiv1aichatsessionsget) | **GET** /api/v1/ai/chat/sessions | List chat sessions|
|[**apiV1AiChatSessionsMessagePost**](#apiv1aichatsessionsmessagepost) | **POST** /api/v1/ai/chat/sessions/message | Chat with Strategy Advisor|
|[**apiV1AiChatSessionsPost**](#apiv1aichatsessionspost) | **POST** /api/v1/ai/chat/sessions | Create a new chat session|
|[**apiV1AiChatSessionsSessionIdMessagesGet**](#apiv1aichatsessionssessionidmessagesget) | **GET** /api/v1/ai/chat/sessions/{session_id}/messages | Get messages for a session|
|[**apiV1AiChatSessionsSessionIdMessagesPost**](#apiv1aichatsessionssessionidmessagespost) | **POST** /api/v1/ai/chat/sessions/{session_id}/messages | Send a message to the AI|
|[**apiV1AiIngestUploadPost**](#apiv1aiingestuploadpost) | **POST** /api/v1/ai/ingest/upload | Upload context file|
|[**apiV1AnalysisCalculateSmcPost**](#apiv1analysiscalculatesmcpost) | **POST** /api/v1/analysis/calculate/smc | Calculate Smart Money Concepts (SMC)|
|[**apiV1AnalysisIndicatorsGet**](#apiv1analysisindicatorsget) | **GET** /api/v1/analysis/indicators | Get multiple technical indicators|
|[**apiV1AnalysisLevelsIndicatorsIndicatorTypeGet**](#apiv1analysislevelsindicatorsindicatortypeget) | **GET** /api/v1/analysis/levels/indicators/{indicator_type} | Get specific indicator data|
|[**apiV1AnalysisOpportunitiesGet**](#apiv1analysisopportunitiesget) | **GET** /api/v1/analysis/opportunities | Get skipped trade opportunities (filtered by Volatility/Sentiment)|
|[**apiV1AuthProfileAvatarPost**](#apiv1authprofileavatarpost) | **POST** /api/v1/auth/profile/avatar | Upload user avatar|
|[**apiV1AuthProfileGet**](#apiv1authprofileget) | **GET** /api/v1/auth/profile | Get current user profile|
|[**apiV1AuthRegisterPost**](#apiv1authregisterpost) | **POST** /api/v1/auth/register | Register a new user|
|[**apiV1AuthTokenPost**](#apiv1authtokenpost) | **POST** /api/v1/auth/token | Login to get access token|
|[**apiV1CoachMentalHistoryPost**](#apiv1coachmentalhistorypost) | **POST** /api/v1/coach/mental-history | Log a Mental Hand History entry|
|[**apiV1DataIngestManualPost**](#apiv1dataingestmanualpost) | **POST** /api/v1/data/ingest/manual | Manually trigger the OANDA data ingestion job.|
|[**apiV1DataOpenInterestAnalysisGet**](#apiv1dataopeninterestanalysisget) | **GET** /api/v1/data/open-interest/analysis | Get Open Interest Analysis|
|[**apiV1DataOpenInterestDetailsGet**](#apiv1dataopeninterestdetailsget) | **GET** /api/v1/data/open-interest/details | Get Open Interest Details|
|[**apiV1DataOpenInterestSnapshotsGet**](#apiv1dataopeninterestsnapshotsget) | **GET** /api/v1/data/open-interest/snapshots | Get Open Interest Snapshots|
|[**apiV1DataOpenInterestUploadPost**](#apiv1dataopeninterestuploadpost) | **POST** /api/v1/data/open-interest/upload | Upload Open Interest Matrix Excel|
|[**apiV1DataSourcesGet**](#apiv1datasourcesget) | **GET** /api/v1/data-sources | List all data sources|
|[**apiV1DataSourcesIdBackfillPost**](#apiv1datasourcesidbackfillpost) | **POST** /api/v1/data-sources/{id}/backfill | Trigger a historical backfill|
|[**apiV1DataSourcesIdDelete**](#apiv1datasourcesiddelete) | **DELETE** /api/v1/data-sources/{id} | Delete a data source|
|[**apiV1DataSourcesIdGet**](#apiv1datasourcesidget) | **GET** /api/v1/data-sources/{id} | Get a specific data source|
|[**apiV1DataSourcesIdPut**](#apiv1datasourcesidput) | **PUT** /api/v1/data-sources/{id} | Update a data source|
|[**apiV1DataSourcesPost**](#apiv1datasourcespost) | **POST** /api/v1/data-sources | Create a new data source|
|[**apiV1DataSymbolsSymbolIdPatch**](#apiv1datasymbolssymbolidpatch) | **PATCH** /api/v1/data/symbols/{symbol_id} | Update symbol status|
|[**apiV1DataSyncPost**](#apiv1datasyncpost) | **POST** /api/v1/data/sync | Trigger manual data sync for a symbol.|
|[**apiV1DataUploadPost**](#apiv1datauploadpost) | **POST** /api/v1/data/upload | Upload historical data CSV|
|[**apiV1DeploymentsGet**](#apiv1deploymentsget) | **GET** /api/v1/deployments/ | List all deployments|
|[**apiV1DeploymentsIdStopPost**](#apiv1deploymentsidstoppost) | **POST** /api/v1/deployments/{id}/stop | Stop a deployment|
|[**apiV1DeploymentsPost**](#apiv1deploymentspost) | **POST** /api/v1/deployments/ | Create a new deployment|
|[**apiV1ExecutionAccountSummaryGet**](#apiv1executionaccountsummaryget) | **GET** /api/v1/execution/account/summary | Get account summary|
|[**apiV1ExecutionTradesSyncGet**](#apiv1executiontradessyncget) | **GET** /api/v1/execution/trades/sync | List trades with filtering and pagination|
|[**apiV1ExecutionTradesTradeIdClosePost**](#apiv1executiontradestradeidclosepost) | **POST** /api/v1/execution/trades/{trade_id}/close | Manually close a trade|
|[**apiV1FoundryValidatePost**](#apiv1foundryvalidatepost) | **POST** /api/v1/foundry/validate | Run Walk-Forward Validation (Proving Ground)|
|[**apiV1FundsFundIdDelete**](#apiv1fundsfundiddelete) | **DELETE** /api/v1/funds/{fund_id} | Delete a fund|
|[**apiV1FundsFundIdGet**](#apiv1fundsfundidget) | **GET** /api/v1/funds/{fund_id} | Get fund details|
|[**apiV1FundsFundIdPut**](#apiv1fundsfundidput) | **PUT** /api/v1/funds/{fund_id} | Update fund details|
|[**apiV1FundsGet**](#apiv1fundsget) | **GET** /api/v1/funds | List funds for current user|
|[**apiV1FundsPost**](#apiv1fundspost) | **POST** /api/v1/funds | Create a new fund|
|[**apiV1InternalSignalsPost**](#apiv1internalsignalspost) | **POST** /api/v1/internal/signals | Report a signal from an internal service|
|[**apiV1JournalEntryIdGet**](#apiv1journalentryidget) | **GET** /api/v1/journal/{entry_id} | Get journal entry details|
|[**apiV1JournalGet**](#apiv1journalget) | **GET** /api/v1/journal/ | List journal entries for current user|
|[**apiV1JournalPost**](#apiv1journalpost) | **POST** /api/v1/journal/ | Create a new journal entry|
|[**apiV1MarketCandlesGet**](#apiv1marketcandlesget) | **GET** /api/v1/market/candles | Fetch historical candle data|
|[**apiV1MarketCategoriesCategoryIdSymbolsPost**](#apiv1marketcategoriescategoryidsymbolspost) | **POST** /api/v1/market/categories/{category_id}/symbols | Add a symbol to a category|
|[**apiV1MarketCategoriesGet**](#apiv1marketcategoriesget) | **GET** /api/v1/market/categories | List market categories|
|[**apiV1MarketCategoriesPost**](#apiv1marketcategoriespost) | **POST** /api/v1/market/categories | Create a new market category|
|[**apiV1MarketSymbolsGet**](#apiv1marketsymbolsget) | **GET** /api/v1/market/symbols | Get active symbols for a broker|
|[**apiV1MarketplaceGet**](#apiv1marketplaceget) | **GET** /api/v1/marketplace | Browse verified strategies|
|[**apiV1PluginsGet**](#apiv1pluginsget) | **GET** /api/v1/plugins | List all plugins|
|[**apiV1PluginsIdActivatePost**](#apiv1pluginsidactivatepost) | **POST** /api/v1/plugins/{id}/activate | Activate a plugin for current user|
|[**apiV1PluginsIdConfigPut**](#apiv1pluginsidconfigput) | **PUT** /api/v1/plugins/{id}/config | Update plugin configuration|
|[**apiV1PluginsIdDeactivatePost**](#apiv1pluginsiddeactivatepost) | **POST** /api/v1/plugins/{id}/deactivate | Deactivate a plugin|
|[**apiV1PromptsGet**](#apiv1promptsget) | **GET** /api/v1/prompts | List system prompts|
|[**apiV1PromptsIdGet**](#apiv1promptsidget) | **GET** /api/v1/prompts/{id} | Get system prompt details|
|[**apiV1PromptsIdPut**](#apiv1promptsidput) | **PUT** /api/v1/prompts/{id} | Update system prompt|
|[**apiV1PromptsIdRenderPost**](#apiv1promptsidrenderpost) | **POST** /api/v1/prompts/{id}/render | Render prompt with variables|
|[**apiV1PromptsPost**](#apiv1promptspost) | **POST** /api/v1/prompts | Create new system prompt|
|[**apiV1RiskCheckPost**](#apiv1riskcheckpost) | **POST** /api/v1/risk/check | Check if a trade execution is allowed based on risk rules|
|[**apiV1RiskPortfolioPost**](#apiv1riskportfoliopost) | **POST** /api/v1/risk/portfolio | Update portfolio risk parity settings|
|[**apiV1SettingsPreferencesGet**](#apiv1settingspreferencesget) | **GET** /api/v1/settings/preferences | Get current user preferences|
|[**apiV1SettingsPreferencesPut**](#apiv1settingspreferencesput) | **PUT** /api/v1/settings/preferences | Update user preferences|
|[**apiV1SignalBatchPost**](#apiv1signalbatchpost) | **POST** /api/v1/signal/batch | Fetch batch signals for multiple symbols|
|[**apiV1SignalCheckPost**](#apiv1signalcheckpost) | **POST** /api/v1/signal/check | Check if a signal is valid given current state|
|[**apiV1SignalDetectedGet**](#apiv1signaldetectedget) | **GET** /api/v1/signal/detected | Get detected signals history|
|[**apiV1SignalLatestSymbolGet**](#apiv1signallatestsymbolget) | **GET** /api/v1/signal/latest/{symbol} | Get the latest signal for a specific symbol|
|[**apiV1StrategiesIdConfigPost**](#apiv1strategiesidconfigpost) | **POST** /api/v1/strategies/{id}/config | Update configuration for a strategy instance|
|[**apiV1StrategiesTemplatesGet**](#apiv1strategiestemplatesget) | **GET** /api/v1/strategies/templates | List available strategy templates|
|[**apiV1StreamPricesGet**](#apiv1streampricesget) | **GET** /api/v1/stream/prices | WebSocket for real-time price updates|
|[**apiV1TransactionsBalanceGet**](#apiv1transactionsbalanceget) | **GET** /api/v1/transactions/balance | Get fund balance|
|[**apiV1TransactionsGet**](#apiv1transactionsget) | **GET** /api/v1/transactions | List transactions|
|[**apiV1TransactionsImportPost**](#apiv1transactionsimportpost) | **POST** /api/v1/transactions/import | Import transactions from Excel|
|[**apiV1TransactionsPost**](#apiv1transactionspost) | **POST** /api/v1/transactions | Create a manual transaction|
|[**backtestCustomPost**](#backtestcustompost) | **POST** /backtest/custom | Run a custom strategy backtest|
|[**backtestMonteCarloPost**](#backtestmontecarlopost) | **POST** /backtest/monte-carlo | Run a Monte Carlo simulation|
|[**backtestOptimizePost**](#backtestoptimizepost) | **POST** /backtest/optimize | Run an optimization job|
|[**backtestResultsBacktestIdGet**](#backtestresultsbacktestidget) | **GET** /backtest/results/{backtest_id} | Get results of a specific backtest|
|[**backtestRunPost**](#backtestrunpost) | **POST** /backtest/run | Trigger a backtest|
|[**savedStrategiesGet**](#savedstrategiesget) | **GET** /saved-strategies | List saved strategies|
|[**savedStrategiesIdDelete**](#savedstrategiesiddelete) | **DELETE** /saved-strategies/{id} | Delete saved strategy|
|[**savedStrategiesIdGet**](#savedstrategiesidget) | **GET** /saved-strategies/{id} | Get saved strategy|
|[**savedStrategiesIdPut**](#savedstrategiesidput) | **PUT** /saved-strategies/{id} | Update saved strategy|
|[**savedStrategiesPost**](#savedstrategiespost) | **POST** /saved-strategies | Create a saved strategy|

# **apiV1AccountsAccountIdDelete**
> APIResponse apiV1AccountsAccountIdDelete()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let accountId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AccountsAccountIdDelete(
    accountId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **accountId** | [**string**] |  | defaults to undefined|


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
|**200** | Account deleted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AccountsAccountIdPut**
> APIResponseBrokerAccount apiV1AccountsAccountIdPut(brokerAccountUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    BrokerAccountUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let accountId: string; // (default to undefined)
let brokerAccountUpdate: BrokerAccountUpdate; //

const { status, data } = await apiInstance.apiV1AccountsAccountIdPut(
    accountId,
    brokerAccountUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **brokerAccountUpdate** | **BrokerAccountUpdate**|  | |
| **accountId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseBrokerAccount**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Account updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AccountsGet**
> APIResponseBrokerAccountList apiV1AccountsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1AccountsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseBrokerAccountList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of broker accounts |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AccountsPost**
> APIResponseBrokerAccount apiV1AccountsPost(brokerAccountCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    BrokerAccountCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let brokerAccountCreate: BrokerAccountCreate; //

const { status, data } = await apiInstance.apiV1AccountsPost(
    brokerAccountCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **brokerAccountCreate** | **BrokerAccountCreate**|  | |


### Return type

**APIResponseBrokerAccount**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Account created |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiAgentObserverRunPost**
> ApiV1AiAgentObserverRunPost200Response apiV1AiAgentObserverRunPost(apiV1AiAgentObserverRunPostRequest)

Trigger the AI Market Observer to analyze a specific request or symbol.

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1AiAgentObserverRunPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let apiV1AiAgentObserverRunPostRequest: ApiV1AiAgentObserverRunPostRequest; //

const { status, data } = await apiInstance.apiV1AiAgentObserverRunPost(
    apiV1AiAgentObserverRunPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1AiAgentObserverRunPostRequest** | **ApiV1AiAgentObserverRunPostRequest**|  | |


### Return type

**ApiV1AiAgentObserverRunPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Agent Report |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiAgentsGet**
> APIResponseAgentList apiV1AiAgentsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1AiAgentsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseAgentList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of agents |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiAgentsIdGet**
> APIResponseAgent apiV1AiAgentsIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AiAgentsIdGet(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseAgent**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Agent details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiBriefingGet**
> APIResponseBriefing apiV1AiBriefingGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1AiBriefingGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseBriefing**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Latest briefing |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiBriefingPost**
> APIResponseBriefing apiV1AiBriefingPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1AiBriefingPost();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseBriefing**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Briefing generated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiChatSessionsGet**
> APIResponseChatSessionList apiV1AiChatSessionsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let strategyId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AiChatSessionsGet(
    strategyId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **strategyId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**APIResponseChatSessionList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of chat sessions |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiChatSessionsMessagePost**
> ApiV1AiChatSessionsMessagePost200Response apiV1AiChatSessionsMessagePost()

Direct chat endpoint for Strategy Advisor agent. Highly latent multi-agent response (up to 300s timeout).

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    StrategyChatRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let strategyChatRequest: StrategyChatRequest; // (optional)

const { status, data } = await apiInstance.apiV1AiChatSessionsMessagePost(
    strategyChatRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **strategyChatRequest** | **StrategyChatRequest**|  | |


### Return type

**ApiV1AiChatSessionsMessagePost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | AI Response |  -  |
|**503** | Agent Unavailable |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiChatSessionsPost**
> APIResponseChatSession apiV1AiChatSessionsPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ChatSessionCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let chatSessionCreate: ChatSessionCreate; // (optional)

const { status, data } = await apiInstance.apiV1AiChatSessionsPost(
    chatSessionCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **chatSessionCreate** | **ChatSessionCreate**|  | |


### Return type

**APIResponseChatSession**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created chat session |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiChatSessionsSessionIdMessagesGet**
> APIResponseChatMessageList apiV1AiChatSessionsSessionIdMessagesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let sessionId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AiChatSessionsSessionIdMessagesGet(
    sessionId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **sessionId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseChatMessageList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of messages |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiChatSessionsSessionIdMessagesPost**
> APIResponseChatMessage apiV1AiChatSessionsSessionIdMessagesPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ChatMessageCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let sessionId: string; // (default to undefined)
let chatMessageCreate: ChatMessageCreate; // (optional)

const { status, data } = await apiInstance.apiV1AiChatSessionsSessionIdMessagesPost(
    sessionId,
    chatMessageCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **chatMessageCreate** | **ChatMessageCreate**|  | |
| **sessionId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseChatMessage**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | AI Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AiIngestUploadPost**
> ApiV1AiIngestUploadPost200Response apiV1AiIngestUploadPost()

Upload a file (PDF, Image) for AI context.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let file: File; // (optional) (default to undefined)
let userId: string; // (optional) (default to undefined)
let contextType: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AiIngestUploadPost(
    file,
    userId,
    contextType
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|
| **userId** | [**string**] |  | (optional) defaults to undefined|
| **contextType** | [**string**] |  | (optional) defaults to undefined|


### Return type

**ApiV1AiIngestUploadPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | File uploaded |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisCalculateSmcPost**
> SMCResponse apiV1AnalysisCalculateSmcPost(sMCRequest)

Detects Order Blocks, FVGs, Liquidity Sweeps, and Market Structure.

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SMCRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let sMCRequest: SMCRequest; //

const { status, data } = await apiInstance.apiV1AnalysisCalculateSmcPost(
    sMCRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **sMCRequest** | **SMCRequest**|  | |


### Return type

**SMCResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | SMC Analysis Result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisIndicatorsGet**
> { [key: string]: Array<object>; } apiV1AnalysisIndicatorsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let snapshotAt: string; // (default to undefined)
let contract: string; // (optional) (default to undefined)
let minOi: number; // (optional) (default to 0)
let maxOi: number; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AnalysisIndicatorsGet(
    snapshotAt,
    contract,
    minOi,
    maxOi
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **snapshotAt** | [**string**] |  | defaults to undefined|
| **contract** | [**string**] |  | (optional) defaults to undefined|
| **minOi** | [**number**] |  | (optional) defaults to 0|
| **maxOi** | [**number**] |  | (optional) defaults to undefined|


### Return type

**{ [key: string]: Array<object>; }**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Calculated indicators |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisLevelsIndicatorsIndicatorTypeGet**
> Array<object> apiV1AnalysisLevelsIndicatorsIndicatorTypeGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let indicatorType: string; // (default to undefined)
let symbol: string; // (default to undefined)
let timeframe: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1AnalysisLevelsIndicatorsIndicatorTypeGet(
    indicatorType,
    symbol,
    timeframe
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **indicatorType** | [**string**] |  | defaults to undefined|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | defaults to undefined|


### Return type

**Array<object>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Indicator data |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AnalysisOpportunitiesGet**
> Array<OpportunityLog> apiV1AnalysisOpportunitiesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let limit: number; // (optional) (default to 50)

const { status, data } = await apiInstance.apiV1AnalysisOpportunitiesGet(
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 50|


### Return type

**Array<OpportunityLog>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of skipped opportunities |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1AuthProfileAvatarPost**
> APIResponseUserResponse apiV1AuthProfileAvatarPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let file: File; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1AuthProfileAvatarPost(
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|


### Return type

**APIResponseUserResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Avatar uploaded successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

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

# **apiV1CoachMentalHistoryPost**
> APIResponse apiV1CoachMentalHistoryPost(mentalHandHistoryCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    MentalHandHistoryCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let mentalHandHistoryCreate: MentalHandHistoryCreate; //

const { status, data } = await apiInstance.apiV1CoachMentalHistoryPost(
    mentalHandHistoryCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **mentalHandHistoryCreate** | **MentalHandHistoryCreate**|  | |


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
|**201** | Entry created |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataIngestManualPost**
> ApiV1DataIngestManualPost202Response apiV1DataIngestManualPost()

This endpoint triggers the background job responsible for fetching recent OANDA candle data across configured symbols and timeframes, and storing it in the database. Returns a 202 Accepted response upon successful triggering of the background task.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let symbol: string; //Optional symbol to ingest (e.g., EUR_USD). If omitted, defaults to configured symbols. (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1DataIngestManualPost(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] | Optional symbol to ingest (e.g., EUR_USD). If omitted, defaults to configured symbols. | (optional) defaults to undefined|


### Return type

**ApiV1DataIngestManualPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Ingestion job triggered in background. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataOpenInterestAnalysisGet**
> APIResponseOpenInterestAnalytics apiV1DataOpenInterestAnalysisGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let snapshotAt: string; //Optional snapshot time (defaults to latest) (optional) (default to undefined)
let contract: string; //Optional contract filter (optional) (default to undefined)
let smartFilter: boolean; //Apply smart range filtering (std dev) (optional) (default to false)

const { status, data } = await apiInstance.apiV1DataOpenInterestAnalysisGet(
    snapshotAt,
    contract,
    smartFilter
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **snapshotAt** | [**string**] | Optional snapshot time (defaults to latest) | (optional) defaults to undefined|
| **contract** | [**string**] | Optional contract filter | (optional) defaults to undefined|
| **smartFilter** | [**boolean**] | Apply smart range filtering (std dev) | (optional) defaults to false|


### Return type

**APIResponseOpenInterestAnalytics**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Analytics data (PCR, Max Pain, Net Delta) |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataOpenInterestDetailsGet**
> Array<OpenInterestCommon> apiV1DataOpenInterestDetailsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let snapshotAt: string; // (default to undefined)
let contract: string; //Optional contract filter (optional) (default to undefined)
let minOi: number; //Minimum OI filter (optional) (default to 2000)
let maxOi: number; //Maximum OI filter (optional) (default to 5500)
let smartFilter: boolean; //Apply smart range filtering (std dev) (optional) (default to false)

const { status, data } = await apiInstance.apiV1DataOpenInterestDetailsGet(
    snapshotAt,
    contract,
    minOi,
    maxOi,
    smartFilter
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **snapshotAt** | [**string**] |  | defaults to undefined|
| **contract** | [**string**] | Optional contract filter | (optional) defaults to undefined|
| **minOi** | [**number**] | Minimum OI filter | (optional) defaults to 2000|
| **maxOi** | [**number**] | Maximum OI filter | (optional) defaults to 5500|
| **smartFilter** | [**boolean**] | Apply smart range filtering (std dev) | (optional) defaults to false|


### Return type

**Array<OpenInterestCommon>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Detailed active OI records |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataOpenInterestSnapshotsGet**
> Array<ApiV1DataOpenInterestSnapshotsGet200ResponseInner> apiV1DataOpenInterestSnapshotsGet()

Returns a list of available Open Interest snapshots.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let limit: number; // (optional) (default to 20)

const { status, data } = await apiInstance.apiV1DataOpenInterestSnapshotsGet(
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 20|


### Return type

**Array<ApiV1DataOpenInterestSnapshotsGet200ResponseInner>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of snapshots |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataOpenInterestUploadPost**
> ApiV1DataOpenInterestUploadPost201Response apiV1DataOpenInterestUploadPost()

Proxies the upload to the data-pipeline service.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let snapshotAt: string; //Optional snapshot timestamp override (optional) (default to undefined)
let file: File; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1DataOpenInterestUploadPost(
    snapshotAt,
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **snapshotAt** | [**string**] | Optional snapshot timestamp override | (optional) defaults to undefined|
| **file** | [**File**] |  | (optional) defaults to undefined|


### Return type

**ApiV1DataOpenInterestUploadPost201Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Data imported successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesGet**
> APIResponseDataSourceList apiV1DataSourcesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1DataSourcesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseDataSourceList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of data sources |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesIdBackfillPost**
> ApiV1DataSourcesIdBackfillPost202Response apiV1DataSourcesIdBackfillPost(apiV1DataSourcesIdBackfillPostRequest)

Proxies the request to the Data Pipeline service to fetch and ingest historical candles.

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1DataSourcesIdBackfillPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let apiV1DataSourcesIdBackfillPostRequest: ApiV1DataSourcesIdBackfillPostRequest; //

const { status, data } = await apiInstance.apiV1DataSourcesIdBackfillPost(
    id,
    apiV1DataSourcesIdBackfillPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1DataSourcesIdBackfillPostRequest** | **ApiV1DataSourcesIdBackfillPostRequest**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1DataSourcesIdBackfillPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Backfill job accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesIdDelete**
> APIResponse apiV1DataSourcesIdDelete()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1DataSourcesIdDelete(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


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
|**200** | Data source deleted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesIdGet**
> APIResponseDataSource apiV1DataSourcesIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1DataSourcesIdGet(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseDataSource**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Data source details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesIdPut**
> APIResponseDataSource apiV1DataSourcesIdPut()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    DataSourceUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let dataSourceUpdate: DataSourceUpdate; // (optional)

const { status, data } = await apiInstance.apiV1DataSourcesIdPut(
    id,
    dataSourceUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **dataSourceUpdate** | **DataSourceUpdate**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseDataSource**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Updated data source |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSourcesPost**
> APIResponseDataSource apiV1DataSourcesPost(dataSourceCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    DataSourceCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let dataSourceCreate: DataSourceCreate; //

const { status, data } = await apiInstance.apiV1DataSourcesPost(
    dataSourceCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **dataSourceCreate** | **DataSourceCreate**|  | |


### Return type

**APIResponseDataSource**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Created data source |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSymbolsSymbolIdPatch**
> MarketSymbolResponse apiV1DataSymbolsSymbolIdPatch(marketSymbolUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    MarketSymbolUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let symbolId: string; // (default to undefined)
let marketSymbolUpdate: MarketSymbolUpdate; //

const { status, data } = await apiInstance.apiV1DataSymbolsSymbolIdPatch(
    symbolId,
    marketSymbolUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **marketSymbolUpdate** | **MarketSymbolUpdate**|  | |
| **symbolId** | [**string**] |  | defaults to undefined|


### Return type

**MarketSymbolResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Symbol updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataSyncPost**
> ApiV1DataSyncPost202Response apiV1DataSyncPost()

Proxies the request to the Data Pipeline service to trigger a manual ingestion job.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let symbol: string; //Symbol to sync (e.g. XAU_USD) (default to undefined)

const { status, data } = await apiInstance.apiV1DataSyncPost(
    symbol
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] | Symbol to sync (e.g. XAU_USD) | defaults to undefined|


### Return type

**ApiV1DataSyncPost202Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Sync triggered |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DataUploadPost**
> ApiV1DataUploadPost200Response apiV1DataUploadPost()

Bulk upload of historical candle data via CSV. Handles large files via Nginx proxy. Supports standard OHLCV formats including MetaTrader and Dukascopy.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let file: File; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1DataUploadPost(
    file
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **file** | [**File**] |  | (optional) defaults to undefined|


### Return type

**ApiV1DataUploadPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Upload successful |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DeploymentsGet**
> APIResponseDeploymentList apiV1DeploymentsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1DeploymentsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseDeploymentList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of deployments |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DeploymentsIdStopPost**
> APIResponseDeployment apiV1DeploymentsIdStopPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1DeploymentsIdStopPost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseDeployment**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Deployment stopped |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1DeploymentsPost**
> APIResponseDeployment apiV1DeploymentsPost(deploymentCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    DeploymentCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let deploymentCreate: DeploymentCreate; //

const { status, data } = await apiInstance.apiV1DeploymentsPost(
    deploymentCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **deploymentCreate** | **DeploymentCreate**|  | |


### Return type

**APIResponseDeployment**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Created deployment |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionAccountSummaryGet**
> APIResponse apiV1ExecutionAccountSummaryGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1ExecutionAccountSummaryGet();
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
|**200** | Account summary |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesSyncGet**
> PaginatedResponseTradeResponse apiV1ExecutionTradesSyncGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let page: number; // (optional) (default to 1)
let perPage: number; // (optional) (default to 20)
let status: 'OPEN' | 'CLOSED' | 'REJECTED' | 'ALL'; // (optional) (default to undefined)
let symbol: string; // (optional) (default to undefined)
let fromDate: string; // (optional) (default to undefined)
let toDate: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1ExecutionTradesSyncGet(
    page,
    perPage,
    status,
    symbol,
    fromDate,
    toDate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **page** | [**number**] |  | (optional) defaults to 1|
| **perPage** | [**number**] |  | (optional) defaults to 20|
| **status** | [**&#39;OPEN&#39; | &#39;CLOSED&#39; | &#39;REJECTED&#39; | &#39;ALL&#39;**]**Array<&#39;OPEN&#39; &#124; &#39;CLOSED&#39; &#124; &#39;REJECTED&#39; &#124; &#39;ALL&#39;>** |  | (optional) defaults to undefined|
| **symbol** | [**string**] |  | (optional) defaults to undefined|
| **fromDate** | [**string**] |  | (optional) defaults to undefined|
| **toDate** | [**string**] |  | (optional) defaults to undefined|


### Return type

**PaginatedResponseTradeResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of trades |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1ExecutionTradesTradeIdClosePost**
> APIResponse apiV1ExecutionTradesTradeIdClosePost()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1ExecutionTradesTradeIdClosePostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let tradeId: string; // (default to undefined)
let apiV1ExecutionTradesTradeIdClosePostRequest: ApiV1ExecutionTradesTradeIdClosePostRequest; // (optional)

const { status, data } = await apiInstance.apiV1ExecutionTradesTradeIdClosePost(
    tradeId,
    apiV1ExecutionTradesTradeIdClosePostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1ExecutionTradesTradeIdClosePostRequest** | **ApiV1ExecutionTradesTradeIdClosePostRequest**|  | |
| **tradeId** | [**string**] |  | defaults to undefined|


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
|**200** | Trade closed successfully |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FoundryValidatePost**
> APIResponseFoundryValidateResponse apiV1FoundryValidatePost(foundryValidateRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    FoundryValidateRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let foundryValidateRequest: FoundryValidateRequest; //

const { status, data } = await apiInstance.apiV1FoundryValidatePost(
    foundryValidateRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **foundryValidateRequest** | **FoundryValidateRequest**|  | |


### Return type

**APIResponseFoundryValidateResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Validation result |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FundsFundIdDelete**
> apiV1FundsFundIdDelete()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1FundsFundIdDelete(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Fund deleted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FundsFundIdGet**
> APIResponseFund apiV1FundsFundIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1FundsFundIdGet(
    fundId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundId** | [**string**] |  | defaults to undefined|


### Return type

**APIResponseFund**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Fund details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1FundsFundIdPut**
> APIResponseFund apiV1FundsFundIdPut(fundUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    FundUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let fundId: string; // (default to undefined)
let fundUpdate: FundUpdate; //

const { status, data } = await apiInstance.apiV1FundsFundIdPut(
    fundId,
    fundUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **fundUpdate** | **FundUpdate**|  | |
| **fundId** | [**string**] |  | defaults to undefined|


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
|**200** | Fund updated |  -  |

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

# **apiV1InternalSignalsPost**
> APIResponse apiV1InternalSignalsPost(apiV1InternalSignalsPostRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1InternalSignalsPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let apiV1InternalSignalsPostRequest: ApiV1InternalSignalsPostRequest; //

const { status, data } = await apiInstance.apiV1InternalSignalsPost(
    apiV1InternalSignalsPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1InternalSignalsPostRequest** | **ApiV1InternalSignalsPostRequest**|  | |


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
|**200** | Signal processed |  -  |

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

# **apiV1MarketCandlesGet**
> Array<Candle> apiV1MarketCandlesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let symbol: string; // (default to undefined)
let timeframe: string; // (default to undefined)
let limit: number; // (optional) (default to 1000)

const { status, data } = await apiInstance.apiV1MarketCandlesGet(
    symbol,
    timeframe,
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **symbol** | [**string**] |  | defaults to undefined|
| **timeframe** | [**string**] |  | defaults to undefined|
| **limit** | [**number**] |  | (optional) defaults to 1000|


### Return type

**Array<Candle>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of candles |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1MarketCategoriesCategoryIdSymbolsPost**
> MarketSymbol apiV1MarketCategoriesCategoryIdSymbolsPost(marketSymbolCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    MarketSymbolCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let categoryId: string; // (default to undefined)
let marketSymbolCreate: MarketSymbolCreate; //

const { status, data } = await apiInstance.apiV1MarketCategoriesCategoryIdSymbolsPost(
    categoryId,
    marketSymbolCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **marketSymbolCreate** | **MarketSymbolCreate**|  | |
| **categoryId** | [**string**] |  | defaults to undefined|


### Return type

**MarketSymbol**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Added symbol |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1MarketCategoriesGet**
> Array<MarketCategory> apiV1MarketCategoriesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1MarketCategoriesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<MarketCategory>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of market categories |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1MarketCategoriesPost**
> MarketCategory apiV1MarketCategoriesPost(marketCategoryCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    MarketCategoryCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let marketCategoryCreate: MarketCategoryCreate; //

const { status, data } = await apiInstance.apiV1MarketCategoriesPost(
    marketCategoryCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **marketCategoryCreate** | **MarketCategoryCreate**|  | |


### Return type

**MarketCategory**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Created category |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1MarketSymbolsGet**
> Array<MarketSymbolResponse> apiV1MarketSymbolsGet()

Returns a list of active market symbols (is_active=True) for the specified data source.

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let broker: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1MarketSymbolsGet(
    broker
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **broker** | [**string**] |  | defaults to undefined|


### Return type

**Array<MarketSymbolResponse>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of active symbols |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1MarketplaceGet**
> APIResponseStrategyList apiV1MarketplaceGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1MarketplaceGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseStrategyList**

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

# **apiV1PluginsGet**
> apiV1PluginsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1PluginsGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of plugins |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PluginsIdActivatePost**
> ApiV1PluginsIdActivatePost200Response apiV1PluginsIdActivatePost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1PluginsIdActivatePost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1PluginsIdActivatePost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Plugin activated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PluginsIdConfigPut**
> apiV1PluginsIdConfigPut(pluginConfigUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    PluginConfigUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let pluginConfigUpdate: PluginConfigUpdate; //

const { status, data } = await apiInstance.apiV1PluginsIdConfigPut(
    id,
    pluginConfigUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **pluginConfigUpdate** | **PluginConfigUpdate**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Configuration updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PluginsIdDeactivatePost**
> apiV1PluginsIdDeactivatePost()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1PluginsIdDeactivatePost(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Plugin deactivated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PromptsGet**
> Array<SystemPromptResponse> apiV1PromptsGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let ownerId: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.apiV1PromptsGet(
    ownerId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **ownerId** | [**string**] |  | (optional) defaults to undefined|


### Return type

**Array<SystemPromptResponse>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of prompts |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PromptsIdGet**
> SystemPromptResponse apiV1PromptsIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.apiV1PromptsIdGet(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**SystemPromptResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Prompt Details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PromptsIdPut**
> SystemPromptResponse apiV1PromptsIdPut()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SystemPromptUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let systemPromptUpdate: SystemPromptUpdate; // (optional)

const { status, data } = await apiInstance.apiV1PromptsIdPut(
    id,
    systemPromptUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **systemPromptUpdate** | **SystemPromptUpdate**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

**SystemPromptResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Prompt updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PromptsIdRenderPost**
> ApiV1PromptsIdRenderPost200Response apiV1PromptsIdRenderPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1PromptsIdRenderPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let apiV1PromptsIdRenderPostRequest: ApiV1PromptsIdRenderPostRequest; // (optional)

const { status, data } = await apiInstance.apiV1PromptsIdRenderPost(
    id,
    apiV1PromptsIdRenderPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1PromptsIdRenderPostRequest** | **ApiV1PromptsIdRenderPostRequest**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

**ApiV1PromptsIdRenderPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Rendered Text |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1PromptsPost**
> SystemPromptResponse apiV1PromptsPost()


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SystemPromptCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let systemPromptCreate: SystemPromptCreate; // (optional)

const { status, data } = await apiInstance.apiV1PromptsPost(
    systemPromptCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **systemPromptCreate** | **SystemPromptCreate**|  | |


### Return type

**SystemPromptResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Prompt Created |  -  |

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

# **apiV1RiskPortfolioPost**
> APIResponse apiV1RiskPortfolioPost(portfolioAllocationUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    PortfolioAllocationUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let portfolioAllocationUpdate: PortfolioAllocationUpdate; //

const { status, data } = await apiInstance.apiV1RiskPortfolioPost(
    portfolioAllocationUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **portfolioAllocationUpdate** | **PortfolioAllocationUpdate**|  | |


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
|**200** | Allocation updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SettingsPreferencesGet**
> APIResponseUserPreferencesResponse apiV1SettingsPreferencesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1SettingsPreferencesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseUserPreferencesResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | User preferences |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SettingsPreferencesPut**
> APIResponseUserPreferencesResponse apiV1SettingsPreferencesPut(updatePreferencesDto)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    UpdatePreferencesDto
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let updatePreferencesDto: UpdatePreferencesDto; //

const { status, data } = await apiInstance.apiV1SettingsPreferencesPut(
    updatePreferencesDto
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **updatePreferencesDto** | **UpdatePreferencesDto**|  | |


### Return type

**APIResponseUserPreferencesResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Updated user preferences |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SignalBatchPost**
> APIResponseSignalList apiV1SignalBatchPost(signalBatchRequest)

Orchestrates symbol discovery, candle fetching, and batch SMC analysis.

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SignalBatchRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let signalBatchRequest: SignalBatchRequest; //

const { status, data } = await apiInstance.apiV1SignalBatchPost(
    signalBatchRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **signalBatchRequest** | **SignalBatchRequest**|  | |


### Return type

**APIResponseSignalList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Batch of signals |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1SignalCheckPost**
> APIResponseSignalResponse apiV1SignalCheckPost(apiV1SignalCheckPostRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    ApiV1SignalCheckPostRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let apiV1SignalCheckPostRequest: ApiV1SignalCheckPostRequest; //

const { status, data } = await apiInstance.apiV1SignalCheckPost(
    apiV1SignalCheckPostRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **apiV1SignalCheckPostRequest** | **ApiV1SignalCheckPostRequest**|  | |


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

# **apiV1SignalDetectedGet**
> APIResponseSignalList apiV1SignalDetectedGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let limit: number; // (optional) (default to 20)

const { status, data } = await apiInstance.apiV1SignalDetectedGet(
    limit
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **limit** | [**number**] |  | (optional) defaults to 20|


### Return type

**APIResponseSignalList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of detected signals |  -  |

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

# **apiV1StrategiesIdConfigPost**
> APIResponseStrategyResponse apiV1StrategiesIdConfigPost(strategyConfigUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    StrategyConfigUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let strategyConfigUpdate: StrategyConfigUpdate; //

const { status, data } = await apiInstance.apiV1StrategiesIdConfigPost(
    id,
    strategyConfigUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **strategyConfigUpdate** | **StrategyConfigUpdate**|  | |
| **id** | [**string**] |  | defaults to undefined|


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
|**200** | Configuration updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StrategiesTemplatesGet**
> APIResponseStrategyTemplateList apiV1StrategiesTemplatesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.apiV1StrategiesTemplatesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIResponseStrategyTemplateList**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | List of strategy templates |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1StreamPricesGet**
> apiV1StreamPricesGet()

Connect via WebSocket to receive real-time tick data for specified symbols. URL: ws://{host}/api/v1/stream/prices 

### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let token: string; //JWT Access Token (default to undefined)
let symbols: string; //Comma-separated list of symbols (e.g., \"EUR_USD,XAU_USD\") (default to undefined)

const { status, data } = await apiInstance.apiV1StreamPricesGet(
    token,
    symbols
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **token** | [**string**] | JWT Access Token | defaults to undefined|
| **symbols** | [**string**] | Comma-separated list of symbols (e.g., \&quot;EUR_USD,XAU_USD\&quot;) | defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**101** | Switching Protocols to WebSocket |  -  |
|**401** | Unauthorized |  -  |

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

# **backtestCustomPost**
> APIResponseBacktestResponse backtestCustomPost(strategyBacktestRequest)

Compiles and runs user-provided Python code against historical data.

### Example

```typescript
import {
    DefaultApi,
    Configuration,
    StrategyBacktestRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let strategyBacktestRequest: StrategyBacktestRequest; //

const { status, data } = await apiInstance.backtestCustomPost(
    strategyBacktestRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **strategyBacktestRequest** | **StrategyBacktestRequest**|  | |


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
|**200** | Custom backtest results |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **backtestMonteCarloPost**
> MonteCarloResponse backtestMonteCarloPost(monteCarloRequest)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    MonteCarloRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

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

**MonteCarloResponse**

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

# **backtestOptimizePost**
> APIResponseBacktestResponse backtestOptimizePost(backtestRequest)


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

const { status, data } = await apiInstance.backtestOptimizePost(
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
|**200** | Optimization results |  -  |

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

# **savedStrategiesGet**
> Array<SavedStrategyResponse> savedStrategiesGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

const { status, data } = await apiInstance.savedStrategiesGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**Array<SavedStrategyResponse>**

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

# **savedStrategiesIdDelete**
> savedStrategiesIdDelete()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.savedStrategiesIdDelete(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**204** | Strategy deleted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **savedStrategiesIdGet**
> SavedStrategyResponse savedStrategiesIdGet()


### Example

```typescript
import {
    DefaultApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)

const { status, data } = await apiInstance.savedStrategiesIdGet(
    id
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **id** | [**string**] |  | defaults to undefined|


### Return type

**SavedStrategyResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Strategy details |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **savedStrategiesIdPut**
> SavedStrategyResponse savedStrategiesIdPut(savedStrategyUpdate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SavedStrategyUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let id: string; // (default to undefined)
let savedStrategyUpdate: SavedStrategyUpdate; //

const { status, data } = await apiInstance.savedStrategiesIdPut(
    id,
    savedStrategyUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **savedStrategyUpdate** | **SavedStrategyUpdate**|  | |
| **id** | [**string**] |  | defaults to undefined|


### Return type

**SavedStrategyResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Strategy updated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **savedStrategiesPost**
> SavedStrategyResponse savedStrategiesPost(savedStrategyCreate)


### Example

```typescript
import {
    DefaultApi,
    Configuration,
    SavedStrategyCreate
} from './api';

const configuration = new Configuration();
const apiInstance = new DefaultApi(configuration);

let savedStrategyCreate: SavedStrategyCreate; //

const { status, data } = await apiInstance.savedStrategiesPost(
    savedStrategyCreate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **savedStrategyCreate** | **SavedStrategyCreate**|  | |


### Return type

**SavedStrategyResponse**

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

