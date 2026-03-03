# TelegramApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**apiV1TelegramConfigurePost**](#apiv1telegramconfigurepost) | **POST** /api/v1/telegram/configure | Configure a personal Telegram bot token (BYOK)|
|[**apiV1TelegramLinkPost**](#apiv1telegramlinkpost) | **POST** /api/v1/telegram/link | Link a Telegram chat_id to the authenticated user|
|[**apiV1TelegramSendPost**](#apiv1telegramsendpost) | **POST** /api/v1/telegram/send | Send a message to the authenticated user\&#39;s Telegram chat|
|[**apiV1TelegramStatusGet**](#apiv1telegramstatusget) | **GET** /api/v1/telegram/status | Get Telegram link status for authenticated user|
|[**apiV1TelegramWebhookPost**](#apiv1telegramwebhookpost) | **POST** /api/v1/telegram/webhook | Receive inbound Telegram updates (Webhook mode — legacy, disabled when polling is active)|

# **apiV1TelegramConfigurePost**
> ConfigureBotResponse apiV1TelegramConfigurePost(configureBotRequest)


### Example

```typescript
import {
    TelegramApi,
    Configuration,
    ConfigureBotRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TelegramApi(configuration);

let configureBotRequest: ConfigureBotRequest; //

const { status, data } = await apiInstance.apiV1TelegramConfigurePost(
    configureBotRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **configureBotRequest** | **ConfigureBotRequest**|  | |


### Return type

**ConfigureBotResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Bot configured |  -  |
|**400** | Invalid bot token |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TelegramLinkPost**
> LinkTelegramResponse apiV1TelegramLinkPost(linkTelegramRequest)


### Example

```typescript
import {
    TelegramApi,
    Configuration,
    LinkTelegramRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TelegramApi(configuration);

let linkTelegramRequest: LinkTelegramRequest; //

const { status, data } = await apiInstance.apiV1TelegramLinkPost(
    linkTelegramRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **linkTelegramRequest** | **LinkTelegramRequest**|  | |


### Return type

**LinkTelegramResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Linked successfully |  -  |
|**400** | chat_id already linked to another user |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TelegramSendPost**
> ApiV1TelegramSendPost200Response apiV1TelegramSendPost(sendTelegramMessageRequest)

Used internally by AI Analyst and other services to push notifications to the user\'s linked Telegram account. 

### Example

```typescript
import {
    TelegramApi,
    Configuration,
    SendTelegramMessageRequest
} from './api';

const configuration = new Configuration();
const apiInstance = new TelegramApi(configuration);

let sendTelegramMessageRequest: SendTelegramMessageRequest; //

const { status, data } = await apiInstance.apiV1TelegramSendPost(
    sendTelegramMessageRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **sendTelegramMessageRequest** | **SendTelegramMessageRequest**|  | |


### Return type

**ApiV1TelegramSendPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Message sent |  -  |
|**404** | No linked Telegram account |  -  |
|**503** | Bot token not configured |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TelegramStatusGet**
> TelegramStatusResponse apiV1TelegramStatusGet()


### Example

```typescript
import {
    TelegramApi,
    Configuration
} from './api';

const configuration = new Configuration();
const apiInstance = new TelegramApi(configuration);

const { status, data } = await apiInstance.apiV1TelegramStatusGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**TelegramStatusResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Telegram link status |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **apiV1TelegramWebhookPost**
> ApiV1TelegramWebhookPost200Response apiV1TelegramWebhookPost(telegramUpdate)

Called by Telegram Bot API when a message arrives. Validates the X-Telegram-Bot-Api-Secret-Token header before processing. **Note:** This endpoint is inactive while TELEGRAM_POLLING_ENABLED=true. 

### Example

```typescript
import {
    TelegramApi,
    Configuration,
    TelegramUpdate
} from './api';

const configuration = new Configuration();
const apiInstance = new TelegramApi(configuration);

let telegramUpdate: TelegramUpdate; //

const { status, data } = await apiInstance.apiV1TelegramWebhookPost(
    telegramUpdate
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **telegramUpdate** | **TelegramUpdate**|  | |


### Return type

**ApiV1TelegramWebhookPost200Response**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Update accepted |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

