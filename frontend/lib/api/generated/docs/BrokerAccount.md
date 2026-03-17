# BrokerAccount


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **string** |  | [optional] [default to undefined]
**fund_id** | **string** |  | [optional] [default to undefined]
**broker_name** | **string** |  | [optional] [default to undefined]
**account_name** | **string** |  | [optional] [default to undefined]
**account_number** | **string** |  | [optional] [default to undefined]
**supported_symbols** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**risk_settings** | **object** |  | [optional] [default to undefined]
**is_active** | **boolean** |  | [optional] [default to undefined]
**is_live** | **boolean** |  | [optional] [default to undefined]
**data_source_id** | **string** |  | [optional] [default to undefined]
**leverage** | **number** |  | [optional] [default to undefined]
**currency** | **string** |  | [optional] [default to undefined]
**balance_snapshot** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { BrokerAccount } from './api';

const instance: BrokerAccount = {
    id,
    fund_id,
    broker_name,
    account_name,
    account_number,
    supported_symbols,
    risk_settings,
    is_active,
    is_live,
    data_source_id,
    leverage,
    currency,
    balance_snapshot,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
