# BacktestResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**metrics** | [**BacktestMetrics**](BacktestMetrics.md) |  | [optional] [default to undefined]
**trades** | **Array&lt;object&gt;** |  | [optional] [default to undefined]
**plot_json** | **string** | Serialized Plotly JSON string | [optional] [default to undefined]

## Example

```typescript
import { BacktestResponse } from './api';

const instance: BacktestResponse = {
    id,
    status,
    metrics,
    trades,
    plot_json,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
