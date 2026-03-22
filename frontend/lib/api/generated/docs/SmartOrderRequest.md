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
**execution_algo** | **string** | Optional execution algorithm (TWAP, VWAP, SCALE_IN) | [optional] [default to undefined]
**algo_params** | **object** | Parameters for the algorithm (e.g., {\&#39;duration\&#39;: 3600}) | [optional] [default to undefined]

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
    execution_algo,
    algo_params,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
