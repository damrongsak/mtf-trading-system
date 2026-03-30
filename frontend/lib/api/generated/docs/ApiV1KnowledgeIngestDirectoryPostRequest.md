# ApiV1KnowledgeIngestDirectoryPostRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**path** | **string** | Absolute or relative path to the directory (e.g., temp/markdown_economics) | [default to undefined]
**force** | **boolean** | If true, re-ingest files even if hash already exists | [optional] [default to false]
**clean_first** | **boolean** | If true, delete the graph before starting ingestion | [optional] [default to false]

## Example

```typescript
import { ApiV1KnowledgeIngestDirectoryPostRequest } from './api';

const instance: ApiV1KnowledgeIngestDirectoryPostRequest = {
    path,
    force,
    clean_first,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
