# RiskCheckRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [default to undefined]
**entry_price** | **number** |  | [default to undefined]
**stop_loss** | **number** |  | [default to undefined]
**take_profit** | **number** |  | [optional] [default to undefined]
**account_balance** | **number** |  | [optional] [default to undefined]
**risk_percentage** | **number** |  | [optional] [default to 1.0]
**risk_usd** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { RiskCheckRequest } from './api';

const instance: RiskCheckRequest = {
    symbol,
    entry_price,
    stop_loss,
    take_profit,
    account_balance,
    risk_percentage,
    risk_usd,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
