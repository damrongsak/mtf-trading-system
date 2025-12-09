# PaginatedResponseJournalEntryResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**ResponseStatus**](ResponseStatus.md) |  | [default to undefined]
**data** | [**Array&lt;JournalEntryResponse&gt;**](JournalEntryResponse.md) |  | [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**meta** | [**Meta**](Meta.md) |  | [default to undefined]
**rate_limit** | [**RateLimitInfo**](RateLimitInfo.md) |  | [optional] [default to undefined]
**timestamp** | **string** |  | [default to undefined]

## Example

```typescript
import { PaginatedResponseJournalEntryResponse } from './api';

const instance: PaginatedResponseJournalEntryResponse = {
    status,
    data,
    message,
    meta,
    rate_limit,
    timestamp,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
