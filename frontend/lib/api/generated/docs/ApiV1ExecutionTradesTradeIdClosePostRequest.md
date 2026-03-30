# ApiV1ExecutionTradesTradeIdClosePostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**price** | **number** | Actual exit price (for local PnL calculation) | [default to undefined]
**broker_account_id** | **string** | Required to identify which account to close on broker | [optional] [default to undefined]
**units** | **number** | Optional: units to close (for partial close). Default is full position. | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionTradesTradeIdClosePostRequest } from './api';

const instance: ApiV1ExecutionTradesTradeIdClosePostRequest = {
    price,
    broker_account_id,
    units,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
