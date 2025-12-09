# AuthTokens


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access_token** | **string** |  | [default to undefined]
**refresh_token** | **string** |  | [optional] [default to undefined]
**token_type** | **string** |  | [optional] [default to 'Bearer']
**expires_in** | **number** |  | [default to undefined]
**expires_at** | **string** |  | [default to undefined]

## Example

```typescript
import { AuthTokens } from './api';

const instance: AuthTokens = {
    access_token,
    refresh_token,
    token_type,
    expires_in,
    expires_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
