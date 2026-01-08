# SMCResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**order_blocks** | [**Array&lt;SMCOrderBlock&gt;**](SMCOrderBlock.md) |  | [optional] [default to undefined]
**fvgs** | [**Array&lt;SMCFVG&gt;**](SMCFVG.md) |  | [optional] [default to undefined]
**liquidity_sweeps** | [**Array&lt;SMCSweep&gt;**](SMCSweep.md) |  | [optional] [default to undefined]
**structure** | [**SMCStructure**](SMCStructure.md) |  | [optional] [default to undefined]
**auto_fibs** | **{ [key: string]: number; }** |  | [optional] [default to undefined]

## Example

```typescript
import { SMCResponse } from './api';

const instance: SMCResponse = {
    order_blocks,
    fvgs,
    liquidity_sweeps,
    structure,
    auto_fibs,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
