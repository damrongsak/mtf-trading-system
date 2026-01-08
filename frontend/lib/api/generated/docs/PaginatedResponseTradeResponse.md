# PaginatedResponseTradeResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**ResponseStatus**](ResponseStatus.md) |  | [default to undefined]
**data** | [**Array&lt;TradeResponse&gt;**](TradeResponse.md) |  | [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**meta** | [**Meta**](Meta.md) |  | [default to undefined]
**timestamp** | **string** |  | [default to undefined]
**rate_limit** | [**RateLimitInfo**](RateLimitInfo.md) |  | [optional] [default to undefined]

## Example

```typescript
import { PaginatedResponseTradeResponse } from './api';

const instance: PaginatedResponseTradeResponse = {
    status,
    data,
    message,
    meta,
    timestamp,
    rate_limit,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
