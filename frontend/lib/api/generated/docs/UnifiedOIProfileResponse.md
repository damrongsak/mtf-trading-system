# UnifiedOIProfileResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**symbol** | **string** |  | [optional] [default to undefined]
**snapshot_at** | **string** |  | [optional] [default to undefined]
**prev_snapshot_at** | **string** |  | [optional] [default to undefined]
**price** | **number** |  | [optional] [default to undefined]
**gamma_regime** | **string** |  | [optional] [default to undefined]
**crowding_regime** | **string** |  | [optional] [default to undefined]
**sentiment_drift** | [**DriftAnalysis**](DriftAnalysis.md) |  | [optional] [default to undefined]
**gamma_levels** | **Array&lt;object&gt;** |  | [optional] [default to undefined]
**summary** | [**AnalysisSummary**](AnalysisSummary.md) |  | [optional] [default to undefined]

## Example

```typescript
import { UnifiedOIProfileResponse } from './api';

const instance: UnifiedOIProfileResponse = {
    symbol,
    snapshot_at,
    prev_snapshot_at,
    price,
    gamma_regime,
    crowding_regime,
    sentiment_drift,
    gamma_levels,
    summary,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
