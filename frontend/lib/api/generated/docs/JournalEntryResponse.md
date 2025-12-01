# JournalEntryResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [default to undefined]
**direction** | **string** |  | [default to undefined]
**session** | **string** |  | [optional] [default to undefined]
**entry_price** | **number** |  | [optional] [default to undefined]
**exit_price** | **number** |  | [optional] [default to undefined]
**pnl_amount** | **number** |  | [optional] [default to undefined]
**pnl_r** | **number** |  | [optional] [default to undefined]
**risk_amount** | **number** |  | [optional] [default to undefined]
**stop_loss_price** | **number** |  | [optional] [default to undefined]
**take_profit_price** | **number** |  | [optional] [default to undefined]
**context_score** | **number** |  | [optional] [default to undefined]
**game_level** | **string** |  | [optional] [default to undefined]
**mental_state** | [**JournalEntryCreateMentalState**](JournalEntryCreateMentalState.md) |  | [optional] [default to undefined]
**timeline_events** | [**Array&lt;JournalEntryCreateTimelineEventsInner&gt;**](JournalEntryCreateTimelineEventsInner.md) |  | [optional] [default to undefined]
**root_cause** | [**JournalEntryCreateRootCause**](JournalEntryCreateRootCause.md) |  | [optional] [default to undefined]
**id** | **string** |  | [optional] [default to undefined]
**user_id** | **string** |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]
**updated_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { JournalEntryResponse } from './api';

const instance: JournalEntryResponse = {
    symbol,
    direction,
    session,
    entry_price,
    exit_price,
    pnl_amount,
    pnl_r,
    risk_amount,
    stop_loss_price,
    take_profit_price,
    context_score,
    game_level,
    mental_state,
    timeline_events,
    root_cause,
    id,
    user_id,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
