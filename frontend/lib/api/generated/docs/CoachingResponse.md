# CoachingResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**psychological_state** | **string** | Detected emotional state (e.g., Revenge Trading, FOMO, Discipline) | [default to undefined]
**advice** | **string** | Specific coaching narrative in Thai or English | [default to undefined]
**confluence_context** | **object** | Market context during recorded journal entries | [optional] [default to undefined]
**suggested_actions** | **Array&lt;string&gt;** |  | [optional] [default to undefined]
**sentiment_trend** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { CoachingResponse } from './api';

const instance: CoachingResponse = {
    psychological_state,
    advice,
    confluence_context,
    suggested_actions,
    sentiment_trend,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
