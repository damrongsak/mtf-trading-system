# UpdatePreferencesDto


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**default_fund_id** | **string** |  | [optional] [default to undefined]
**strategy_type** | **string** |  | [optional] [default to undefined]
**asset_classes** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**max_risk_per_trade** | **number** |  | [optional] [default to undefined]
**default_lot_size** | **number** |  | [optional] [default to undefined]
**max_drawdown_threshold** | **number** |  | [optional] [default to undefined]
**max_portfolio_beta** | **number** |  | [optional] [default to undefined]
**gross_exposure_limit** | **number** |  | [optional] [default to undefined]
**net_exposure_limit** | **number** |  | [optional] [default to undefined]
**position_limit_single** | **number** |  | [optional] [default to undefined]
**position_limit_sector** | **number** |  | [optional] [default to undefined]
**preferred_timeframes** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**default_symbol** | **string** |  | [optional] [default to undefined]
**session_preferences** | **Array&lt;string&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { UpdatePreferencesDto } from './api';

const instance: UpdatePreferencesDto = {
    default_fund_id,
    strategy_type,
    asset_classes,
    max_risk_per_trade,
    default_lot_size,
    max_drawdown_threshold,
    max_portfolio_beta,
    gross_exposure_limit,
    net_exposure_limit,
    position_limit_single,
    position_limit_sector,
    preferred_timeframes,
    default_symbol,
    session_preferences,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
