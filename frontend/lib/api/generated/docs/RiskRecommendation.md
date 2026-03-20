# RiskRecommendation


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**risk_percentage** | **number** | Suggested risk percentage per trade | [default to undefined]
**max_drawdown_threshold** | **number** | Suggested maximum drawdown threshold | [default to undefined]
**reasoning** | **string** | AI rationale for the recommendation | [default to undefined]

## Example

```typescript
import { RiskRecommendation } from './api';

const instance: RiskRecommendation = {
    risk_percentage,
    max_drawdown_threshold,
    reasoning,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
