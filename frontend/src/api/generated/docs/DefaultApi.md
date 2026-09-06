# DentalClaimsEngine.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**healthCheckHealthGet**](DefaultApi.md#healthCheckHealthGet) | **GET** /health | Health Check



## healthCheckHealthGet

> {String: String} healthCheckHealthGet()

Health Check

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.DefaultApi();
apiInstance.healthCheckHealthGet().then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters

This endpoint does not need any parameter.

### Return type

**{String: String}**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

