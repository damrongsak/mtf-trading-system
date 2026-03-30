# ApiV1ExecutionOrdersOrderIdPutRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**units** | **number** | Signed order units (positive for BUY, negative for SELL). | [optional] [default to undefined]
**price** | **number** | New limit price | [optional] [default to undefined]
**stop_price** | **number** | New trigger price (for STOP/STOP_LIMIT) | [optional] [default to undefined]
**sl_price** | **number** |  | [optional] [default to undefined]
**tp_price** | **number** |  | [optional] [default to undefined]
**trailing_sl** | **boolean** | Enable/Disable trailing stop loss | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionOrdersOrderIdPutRequest } from './api';

const instance: ApiV1ExecutionOrdersOrderIdPutRequest = {
    broker_account_id,
    units,
    price,
    stop_price,
    sl_price,
    tp_price,
    trailing_sl,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
