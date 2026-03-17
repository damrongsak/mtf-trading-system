# BrokerAccountCreate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**fund_id** | **string** |  | [default to undefined]
**broker_name** | **string** |  | [default to undefined]
**account_name** | **string** |  | [default to undefined]
**account_number** | **string** |  | [optional] [default to undefined]
**credentials** | **object** |  | [default to undefined]
**supported_symbols** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**risk_settings** | **object** |  | [optional] [default to undefined]
**data_source_id** | **string** |  | [optional] [default to undefined]
**leverage** | **number** |  | [optional] [default to undefined]
**currency** | **string** |  | [optional] [default to undefined]
**balance_snapshot** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { BrokerAccountCreate } from './api';

const instance: BrokerAccountCreate = {
    fund_id,
    broker_name,
    account_name,
    account_number,
    credentials,
    supported_symbols,
    risk_settings,
    data_source_id,
    leverage,
    currency,
    balance_snapshot,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
