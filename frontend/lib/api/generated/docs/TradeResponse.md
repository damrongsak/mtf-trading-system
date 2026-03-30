# TradeResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trade_id** | **string** |  | [default to undefined]
**symbol** | **string** |  | [default to undefined]
**strategy_name** | **string** |  | [default to undefined]
**signal_timestamp** | **string** |  | [default to undefined]
**direction** | [**TradeDirection**](TradeDirection.md) |  | [default to undefined]
**entry_price** | **number** |  | [default to undefined]
**sl_price** | **number** |  | [default to undefined]
**tp_price** | **number** |  | [default to undefined]
**lot_size** | **number** |  | [default to undefined]
**risk_usd** | **number** |  | [default to undefined]
**status** | [**TradeStatus**](TradeStatus.md) |  | [default to undefined]
**pnl_usd** | **number** |  | [optional] [default to undefined]
**exit_price** | **number** |  | [optional] [default to undefined]
**exit_timestamp** | **string** |  | [optional] [default to undefined]
**rejection_reason** | **string** |  | [optional] [default to undefined]
**broker_trade_id** | **string** |  | [optional] [default to undefined]
**broker_deal_id** | **string** |  | [optional] [default to undefined]
**execution_latency_ms** | **number** |  | [optional] [default to undefined]
**slippage_pips** | **number** |  | [optional] [default to undefined]
**slippage_ms** | **number** |  | [optional] [default to undefined]
**broker_raw_pnl** | **number** |  | [optional] [default to undefined]
**broker_commission** | **number** |  | [optional] [default to undefined]
**broker_swap** | **number** |  | [optional] [default to undefined]
**reconciled_at** | **string** |  | [optional] [default to undefined]
**reconciliation_status** | **string** |  | [optional] [default to 'PENDING']
**created_at** | **string** |  | [default to undefined]
**updated_at** | **string** |  | [default to undefined]

## Example

```typescript
import { TradeResponse } from './api';

const instance: TradeResponse = {
    trade_id,
    symbol,
    strategy_name,
    signal_timestamp,
    direction,
    entry_price,
    sl_price,
    tp_price,
    lot_size,
    risk_usd,
    status,
    pnl_usd,
    exit_price,
    exit_timestamp,
    rejection_reason,
    broker_trade_id,
    broker_deal_id,
    execution_latency_ms,
    slippage_pips,
    slippage_ms,
    broker_raw_pnl,
    broker_commission,
    broker_swap,
    reconciled_at,
    reconciliation_status,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
