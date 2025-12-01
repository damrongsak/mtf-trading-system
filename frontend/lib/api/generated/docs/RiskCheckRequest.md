# RiskCheckRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**risk_usd** | **number** | Maximum risk in USD allowed for this trade | [default to undefined]
**sl_distance_usd** | **number** | Distance to stop loss in USD (per unit/contract) | [default to undefined]
**min_lot** | **number** | Minimum allowed lot size (e.g., 0.01) | [default to undefined]

## Example

```typescript
import { RiskCheckRequest } from './api';

const instance: RiskCheckRequest = {
    risk_usd,
    sl_distance_usd,
    min_lot,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
