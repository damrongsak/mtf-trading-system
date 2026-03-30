# RiskParityData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbols** | [**Array&lt;RiskParityDataSymbolsInner&gt;**](RiskParityDataSymbolsInner.md) |  | [optional] [default to undefined]
**market_integration_score** | **number** |  | [optional] [default to undefined]
**systemic_alert** | **boolean** |  | [optional] [default to undefined]
**last_rebalanced** | **string** |  | [optional] [default to undefined]
**rebalance_interval_hours** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { RiskParityData } from './api';

const instance: RiskParityData = {
    symbols,
    market_integration_score,
    systemic_alert,
    last_rebalanced,
    rebalance_interval_hours,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
