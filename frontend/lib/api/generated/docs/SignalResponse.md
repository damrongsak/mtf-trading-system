# SignalResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [optional] [default to undefined]
**timeframe** | **string** |  | [optional] [default to undefined]
**timestamp** | **string** |  | [optional] [default to undefined]
**direction** | **string** |  | [optional] [default to undefined]
**entry_price** | **number** |  | [optional] [default to undefined]
**sl_price** | **number** |  | [optional] [default to undefined]
**tp_price** | **number** |  | [optional] [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]
**broker** | **string** |  | [optional] [default to undefined]
**strategy_name** | **string** |  | [optional] [default to undefined]
**confidence** | **number** |  | [optional] [default to 0.0]
**sentiment_score** | **number** | Market sentiment (-1.0 to 1.0) | [optional] [default to undefined]
**sentiment_reason** | **string** |  | [optional] [default to undefined]
**knowledge_context** | **object** | Semantic summary from Knowledge Graph (FalkorDB) at time of signal | [optional] [default to undefined]
**knowledge_score** | **number** | Semantic multiplier (0.5x to 1.5x) based on Knowledge context | [optional] [default to undefined]
**user_id** | **string** |  | [optional] [default to undefined]
**fund_id** | **string** |  | [optional] [default to undefined]
**broker_account_id** | **string** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**filled_price** | **number** |  | [optional] [default to undefined]
**filled_time** | **string** |  | [optional] [default to undefined]
**commission** | **number** |  | [optional] [default to undefined]

## Example

```typescript
import { SignalResponse } from './api';

const instance: SignalResponse = {
    symbol,
    timeframe,
    timestamp,
    direction,
    entry_price,
    sl_price,
    tp_price,
    reason,
    broker,
    strategy_name,
    confidence,
    sentiment_score,
    sentiment_reason,
    knowledge_context,
    knowledge_score,
    user_id,
    fund_id,
    broker_account_id,
    status,
    filled_price,
    filled_time,
    commission,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
