# ApiV1ExecutionTradesTradeIdAmendPostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**sl_price** | **number** |  | [optional] [default to undefined]
**tp_price** | **number** |  | [optional] [default to undefined]
**trailing_sl** | **boolean** | Enable/Disable trailing stop loss | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionTradesTradeIdAmendPostRequest } from './api';

const instance: ApiV1ExecutionTradesTradeIdAmendPostRequest = {
    broker_account_id,
    sl_price,
    tp_price,
    trailing_sl,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
