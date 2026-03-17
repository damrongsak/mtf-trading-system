# AIThinkRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **string** | User input or command | [default to undefined]
**intent** | **string** | Optional hint for the orchestrator (e.g. \&#39;briefing\&#39;, \&#39;market_analysis\&#39;) | [optional] [default to undefined]
**context** | **object** | Additional dynamic context (deployment_id, strategy_id, symbol) | [optional] [default to undefined]
**image_b64** | **string** | Optional base64 encoded image for multimodal analysis | [optional] [default to undefined]

## Example

```typescript
import { AIThinkRequest } from './api';

const instance: AIThinkRequest = {
    message,
    intent,
    context,
    image_b64,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
