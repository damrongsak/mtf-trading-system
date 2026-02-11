# APIResponseFoundryAssembleResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | [**ResponseStatus**](ResponseStatus.md) |  | [default to undefined]
**data** | [**FoundryAssembleResponse**](FoundryAssembleResponse.md) |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**errors** | [**Array&lt;ErrorDetail&gt;**](ErrorDetail.md) |  | [optional] [default to undefined]
**meta** | [**Meta**](Meta.md) |  | [optional] [default to undefined]
**auth** | [**AuthTokens**](AuthTokens.md) |  | [optional] [default to undefined]
**rate_limit** | [**RateLimitInfo**](RateLimitInfo.md) |  | [optional] [default to undefined]
**timestamp** | **string** |  | [default to undefined]

## Example

```typescript
import { APIResponseFoundryAssembleResponse } from './api';

const instance: APIResponseFoundryAssembleResponse = {
    status,
    data,
    message,
    errors,
    meta,
    auth,
    rate_limit,
    timestamp,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
