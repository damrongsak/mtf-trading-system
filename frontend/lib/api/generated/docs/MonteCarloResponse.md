# MonteCarloResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**iterations** | **number** |  | [optional] [default to undefined]
**mode** | **string** |  | [optional] [default to undefined]
**max_drawdown** | **object** |  | [optional] [default to undefined]
**total_return** | **object** |  | [optional] [default to undefined]
**sharpe_ratio** | **object** |  | [optional] [default to undefined]
**ruin_probability** | **number** |  | [optional] [default to undefined]
**equity_curves** | **Array&lt;Array&lt;number&gt;&gt;** |  | [optional] [default to undefined]
**confidence_bands** | **object** |  | [optional] [default to undefined]

## Example

```typescript
import { MonteCarloResponse } from './api';

const instance: MonteCarloResponse = {
    iterations,
    mode,
    max_drawdown,
    total_return,
    sharpe_ratio,
    ruin_probability,
    equity_curves,
    confidence_bands,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
