# ApiV1ExecutionOrdersOrderIdPutRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**units** | **number** | Signed order units (positive for BUY, negative for SELL). | [optional] [default to undefined]
**price** | **number** |  | [optional] [default to undefined]
**stop_loss** | **number** |  | [optional] [default to undefined]
**take_profit** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionOrdersOrderIdPutRequest } from './api';

const instance: ApiV1ExecutionOrdersOrderIdPutRequest = {
    broker_account_id,
    units,
    price,
    stop_loss,
    take_profit,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
