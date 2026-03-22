# Candle


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**time** | **string** |  | [default to undefined]
**open** | **number** |  | [default to undefined]
**high** | **number** |  | [default to undefined]
**low** | **number** |  | [default to undefined]
**close** | **number** |  | [default to undefined]
**volume** | **number** |  | [default to undefined]
**is_complete** | **boolean** |  | [optional] [default to undefined]
**ai_labels** | **object** | Automated labels (e.g., fake_sweep, expansion_confirmed) | [optional] [default to undefined]
**regime_tag** | **string** | Market regime classification | [optional] [default to undefined]

## Example

```typescript
import { Candle } from './api';

const instance: Candle = {
    time,
    open,
    high,
    low,
    close,
    volume,
    is_complete,
    ai_labels,
    regime_tag,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
