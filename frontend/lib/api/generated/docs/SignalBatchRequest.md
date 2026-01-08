# SignalBatchRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker** | **string** | Broker name (e.g. OANDA) | [optional] [default to undefined]
**symbols** | **Array&lt;string&gt;** | Optional list of symbols to override broker defaults | [optional] [default to undefined]

## Example

```typescript
import { SignalBatchRequest } from './api';

const instance: SignalBatchRequest = {
    broker,
    symbols,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
