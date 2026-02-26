# SMCRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [default to undefined]
**timeframe** | **string** |  | [optional] [default to 'H1']
**open** | **Array&lt;number&gt;** |  | [default to undefined]
**high** | **Array&lt;number&gt;** |  | [default to undefined]
**low** | **Array&lt;number&gt;** |  | [default to undefined]
**close** | **Array&lt;number&gt;** |  | [default to undefined]
**volume** | **Array&lt;number&gt;** |  | [optional] [default to undefined]
**timestamps** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**oi_call** | **Array&lt;number&gt;** |  | [optional] [default to undefined]
**oi_put** | **Array&lt;number&gt;** |  | [optional] [default to undefined]
**oi_strikes** | **Array&lt;number&gt;** |  | [optional] [default to undefined]

## Example

```typescript
import { SMCRequest } from './api';

const instance: SMCRequest = {
    symbol,
    timeframe,
    open,
    high,
    low,
    close,
    volume,
    timestamps,
    oi_call,
    oi_put,
    oi_strikes,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
