# RiskCheckResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [optional] [default to undefined]
**direction** | **string** |  | [optional] [default to undefined]
**risk_reward_ratio** | **number** |  | [optional] [default to undefined]
**position_size** | [**RiskCheckResponsePositionSize**](RiskCheckResponsePositionSize.md) |  | [optional] [default to undefined]
**financials** | [**RiskCheckResponseFinancials**](RiskCheckResponseFinancials.md) |  | [optional] [default to undefined]
**is_safe** | **boolean** |  | [optional] [default to undefined]
**warnings** | **Array&lt;string&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { RiskCheckResponse } from './api';

const instance: RiskCheckResponse = {
    symbol,
    direction,
    risk_reward_ratio,
    position_size,
    financials,
    is_safe,
    warnings,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
