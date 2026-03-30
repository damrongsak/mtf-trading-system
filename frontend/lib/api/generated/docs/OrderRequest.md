# OrderRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**broker_account_id** | **string** |  | [default to undefined]
**symbol** | **string** |  | [default to undefined]
**units** | **number** | Absolute order units (strictly positive). Direction is determined by \&#39;side\&#39;. | [default to undefined]
**side** | **string** | Mandatory direction for the order. | [default to undefined]
**order_type** | **string** |  | [default to undefined]
**price** | **number** | Limit price (Required for LIMIT/STOP_LIMIT) | [optional] [default to undefined]
**stop_price** | **number** | Trigger price (Required for STOP/STOP_LIMIT) | [optional] [default to undefined]
**sl_price** | **number** |  | [optional] [default to undefined]
**tp_price** | **number** |  | [optional] [default to undefined]
**trailing_sl** | **boolean** |  | [optional] [default to undefined]
**slippage_pips** | **number** |  | [optional] [default to undefined]
**comment** | **string** |  | [optional] [default to undefined]
**tag** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { OrderRequest } from './api';

const instance: OrderRequest = {
    broker_account_id,
    symbol,
    units,
    side,
    order_type,
    price,
    stop_price,
    sl_price,
    tp_price,
    trailing_sl,
    slippage_pips,
    comment,
    tag,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
