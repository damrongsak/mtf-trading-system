# SmartOrderRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**symbol** | **string** |  | [default to undefined]
**direction** | **string** |  | [default to undefined]
**stop_loss** | **number** |  | [optional] [default to undefined]
**generated_by** | **string** |  | [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]
**risk_usd** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { SmartOrderRequest } from './api';

const instance: SmartOrderRequest = {
    broker_account_id,
    symbol,
    direction,
    stop_loss,
    generated_by,
    reason,
    risk_usd,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
