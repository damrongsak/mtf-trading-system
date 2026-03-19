# DeploymentCreate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**strategy_id** | **string** |  | [default to undefined]
**stock_symbol** | **string** |  | [default to undefined]
**timeframe** | **string** |  | [default to undefined]
**is_live** | **boolean** |  | [optional] [default to undefined]
**config_snapshot** | **object** |  | [default to undefined]
**is_shadow** | **boolean** |  | [optional] [default to false]

## Example

```typescript
import { DeploymentCreate } from './api';

const instance: DeploymentCreate = {
    strategy_id,
    stock_symbol,
    timeframe,
    is_live,
    config_snapshot,
    is_shadow,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
