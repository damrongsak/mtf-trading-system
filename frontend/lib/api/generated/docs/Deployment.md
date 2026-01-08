# Deployment


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**strategy_id** | **string** |  | [optional] [default to undefined]
**stock_symbol** | **string** |  | [optional] [default to undefined]
**timeframe** | **string** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**is_live** | **boolean** |  | [optional] [default to undefined]
**config_snapshot** | **object** |  | [optional] [default to undefined]
**last_error** | **string** |  | [optional] [default to undefined]
**started_at** | **string** |  | [optional] [default to undefined]
**stopped_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { Deployment } from './api';

const instance: Deployment = {
    id,
    strategy_id,
    stock_symbol,
    timeframe,
    status,
    is_live,
    config_snapshot,
    last_error,
    started_at,
    stopped_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
