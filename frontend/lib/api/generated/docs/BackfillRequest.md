# BackfillRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [default to undefined]
**timeframe** | **string** | Specific timeframe or \&#39;ALL\&#39; for all supported timeframes | [optional] [default to 'ALL']
**timeframes** | **Array&lt;string&gt;** | Optional list of specific timeframes to backfill | [optional] [default to undefined]
**count** | **number** |  | [optional] [default to 500]
**from_date** | **string** |  | [optional] [default to undefined]
**to_date** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { BackfillRequest } from './api';

const instance: BackfillRequest = {
    symbol,
    timeframe,
    timeframes,
    count,
    from_date,
    to_date,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
