# PostMortemResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**trade_id** | **string** |  | [optional] [default to undefined]
**summary** | **string** | One-sentence executive summary of the trade result | [optional] [default to undefined]
**execution_quality** | **string** | Assessment of entry/exit quality and slippage | [optional] [default to undefined]
**psychological_analysis** | **string** | Analysis of emotional state and decision making | [optional] [default to undefined]
**alpha_lesson** | **string** | Key takeaway for future strategy performance | [optional] [default to undefined]
**metrics** | [**PostMortemResponseMetrics**](PostMortemResponseMetrics.md) |  | [optional] [default to undefined]
**created_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { PostMortemResponse } from './api';

const instance: PostMortemResponse = {
    trade_id,
    summary,
    execution_quality,
    psychological_analysis,
    alpha_lesson,
    metrics,
    created_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
