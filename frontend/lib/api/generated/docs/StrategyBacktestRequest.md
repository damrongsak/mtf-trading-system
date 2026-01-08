# StrategyBacktestRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**code** | **string** | Python code implementing strategy(data) -&gt; entries, exits | [default to undefined]
**symbol** | **string** |  | [default to undefined]
**timeframe** | **string** |  | [default to undefined]
**start_date** | **string** |  | [default to undefined]
**end_date** | **string** |  | [default to undefined]
**fees** | **number** |  | [optional] [default to undefined]
**slippage** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { StrategyBacktestRequest } from './api';

const instance: StrategyBacktestRequest = {
    code,
    symbol,
    timeframe,
    start_date,
    end_date,
    fees,
    slippage,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
