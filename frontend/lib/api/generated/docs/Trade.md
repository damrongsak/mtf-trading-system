# Trade


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trade_id** | **string** |  | [default to undefined]
**strategy_run_id** | **string** |  | [optional] [default to undefined]
**broker_account_id** | **string** |  | [optional] [default to undefined]
**symbol** | **string** |  | [default to undefined]
**strategy_name** | **string** |  | [default to undefined]
**signal_timestamp** | **string** |  | [default to undefined]
**trace_id** | **string** | Unique HFT-lite execution trace identifier (Redis backed) | [optional] [default to undefined]
**status** | **string** |  | [default to undefined]
**rejection_reason** | **string** |  | [optional] [default to undefined]
**direction** | **string** |  | [default to undefined]
**entry_price** | **number** |  | [default to undefined]
**sl_price** | **number** |  | [optional] [default to undefined]
**tp_price** | **number** |  | [optional] [default to undefined]
**lot_size** | **number** |  | [default to undefined]
**risk_usd** | **number** |  | [default to undefined]
**atr_pips** | **number** |  | [optional] [default to undefined]
**rr_ratio** | **number** |  | [optional] [default to undefined]
**pnl_usd** | **number** |  | [optional] [default to undefined]
**mae_usd** | **number** |  | [optional] [default to undefined]
**mfe_usd** | **number** |  | [optional] [default to undefined]
**exit_price** | **number** |  | [optional] [default to undefined]
**exit_timestamp** | **string** |  | [optional] [default to undefined]
**metadata_json** | **object** |  | [optional] [default to undefined]

## Example

```typescript
import { Trade } from './api';

const instance: Trade = {
    trade_id,
    strategy_run_id,
    broker_account_id,
    symbol,
    strategy_name,
    signal_timestamp,
    trace_id,
    status,
    rejection_reason,
    direction,
    entry_price,
    sl_price,
    tp_price,
    lot_size,
    risk_usd,
    atr_pips,
    rr_ratio,
    pnl_usd,
    mae_usd,
    mfe_usd,
    exit_price,
    exit_timestamp,
    metadata_json,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
