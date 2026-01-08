# DataSource


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**name** | **string** |  | [default to undefined]
**provider** | [**DataSourceProvider**](DataSourceProvider.md) |  | [default to undefined]
**type** | [**DataSourceType**](DataSourceType.md) |  | [default to undefined]
**config_json** | **object** |  | [default to undefined]
**is_active** | **boolean** |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { DataSource } from './api';

const instance: DataSource = {
    id,
    name,
    provider,
    type,
    config_json,
    is_active,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
