# ApiV1SignalCheckPostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**fund_id** | **string** |  | [optional] [default to undefined]
**symbol** | **string** |  | [optional] [default to undefined]
**direction** | **string** |  | [optional] [default to undefined]
**stop_loss** | **number** |  | [optional] [default to undefined]
**risk_usd** | **number** | Optional override for risk calculation | [optional] [default to undefined]
**generated_by** | **string** |  | [optional] [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ApiV1SignalCheckPostRequest } from './api';

const instance: ApiV1SignalCheckPostRequest = {
    fund_id,
    symbol,
    direction,
    stop_loss,
    risk_usd,
    generated_by,
    reason,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
