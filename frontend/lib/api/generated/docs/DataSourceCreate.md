# DataSourceCreate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** |  | [default to undefined]
**provider** | [**DataSourceProvider**](DataSourceProvider.md) |  | [default to undefined]
**type** | [**DataSourceType**](DataSourceType.md) |  | [default to undefined]
**config_json** | **object** |  | [default to undefined]
**is_active** | **boolean** |  | [optional] [default to undefined]

## Example

```typescript
import { DataSourceCreate } from './api';

const instance: DataSourceCreate = {
    name,
    provider,
    type,
    config_json,
    is_active,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
