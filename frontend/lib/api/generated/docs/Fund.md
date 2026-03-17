# Fund


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**name** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**strategy_type** | **string** |  | [optional] [default to undefined]
**asset_classes** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**max_risk_per_trade** | **number** |  | [optional] [default to undefined]
**risk_percentage** | **number** | Dynamic risk per trade as % of NAV (e.g. 0.01 &#x3D; 1%) | [optional] [default to undefined]
**default_lot_size** | **number** |  | [optional] [default to undefined]
**max_drawdown_threshold** | **number** |  | [optional] [default to undefined]
**max_portfolio_beta** | **number** |  | [optional] [default to undefined]
**gross_exposure_limit** | **number** |  | [optional] [default to undefined]
**net_exposure_limit** | **number** |  | [optional] [default to undefined]
**position_limit_single** | **number** |  | [optional] [default to undefined]
**position_limit_sector** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { Fund } from './api';

const instance: Fund = {
    id,
    name,
    description,
    strategy_type,
    asset_classes,
    max_risk_per_trade,
    risk_percentage,
    default_lot_size,
    max_drawdown_threshold,
    max_portfolio_beta,
    gross_exposure_limit,
    net_exposure_limit,
    position_limit_single,
    position_limit_sector,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
