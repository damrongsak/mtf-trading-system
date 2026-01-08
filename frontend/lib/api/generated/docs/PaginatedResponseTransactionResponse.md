# PaginatedResponseTransactionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**ResponseStatus**](ResponseStatus.md) |  | [default to undefined]
**data** | [**Array&lt;TransactionResponse&gt;**](TransactionResponse.md) |  | [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**meta** | [**Meta**](Meta.md) |  | [default to undefined]
**timestamp** | **string** |  | [default to undefined]

## Example

```typescript
import { PaginatedResponseTransactionResponse } from './api';

const instance: PaginatedResponseTransactionResponse = {
    status,
    data,
    message,
    meta,
    timestamp,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
