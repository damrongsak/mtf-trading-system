# APIResponseDataSource


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **string** |  | [optional] [default to undefined]
**message** | **string** |  | [optional] [default to undefined]
**data** | [**DataSource**](DataSource.md) |  | [optional] [default to undefined]
**code** | **string** | Python code defining the strategy (async def strategy...) | [optional] [default to undefined]
**symbol** | **string** |  | [optional] [default to undefined]
**timeframe** | **string** |  | [optional] [default to undefined]
**start_date** | **string** |  | [optional] [default to undefined]
**end_date** | **string** |  | [optional] [default to undefined]
**initial_capital** | **number** |  | [optional] [default to 10000.0]

## Example

```typescript
import { APIResponseDataSource } from './api';

const instance: APIResponseDataSource = {
    status,
    message,
    data,
    code,
    symbol,
    timeframe,
    start_date,
    end_date,
    initial_capital,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
