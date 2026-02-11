# ApiV1ExecutionTradesSyncPostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** | The internal Broker Account ID | [default to undefined]
**lookback_days** | **number** | Number of days to look back for history (default 30) | [optional] [default to undefined]

## Example

```typescript
import { ApiV1ExecutionTradesSyncPostRequest } from './api';

const instance: ApiV1ExecutionTradesSyncPostRequest = {
    broker_account_id,
    lookback_days,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
