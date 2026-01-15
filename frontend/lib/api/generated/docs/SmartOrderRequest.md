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
**confidence** | **number** |  | [optional] [default to 1.0]
**pain_threshold** | **number** |  | [optional] [default to 10.0]
**atr_multiplier** | **number** |  | [optional] [default to 1.0]

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
    confidence,
    pain_threshold,
    atr_multiplier,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
