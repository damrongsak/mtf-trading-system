# TransactionCreate


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**fund_id** | **string** |  | [default to undefined]
**transaction_date** | **string** |  | [default to undefined]
**type** | **string** |  | [default to undefined]
**amount** | **number** |  | [default to undefined]
**currency** | **string** |  | [optional] [default to 'USD']
**status** | **string** |  | [optional] [default to undefined]
**reference** | **string** |  | [optional] [default to undefined]
**description** | **string** |  | [optional] [default to undefined]
**payment_method** | **string** |  | [optional] [default to undefined]
**trading_account** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { TransactionCreate } from './api';

const instance: TransactionCreate = {
    fund_id,
    transaction_date,
    type,
    amount,
    currency,
    status,
    reference,
    description,
    payment_method,
    trading_account,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
