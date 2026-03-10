# ApiV1ExecutionTradesTradeIdAmendPostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**stop_loss** | **number** |  | [optional] [default to undefined]
**take_profit** | **number** |  | [optional] [default to undefined]
**trailing_stop** | **boolean** | Enable/Disable trailing stop loss | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionTradesTradeIdAmendPostRequest } from './api';

const instance: ApiV1ExecutionTradesTradeIdAmendPostRequest = {
    broker_account_id,
    stop_loss,
    take_profit,
    trailing_stop,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
