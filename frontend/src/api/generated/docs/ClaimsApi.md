# FastApi.ClaimsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**createClaimV1ClaimsPost**](ClaimsApi.md#createClaimV1ClaimsPost) | **POST** /v1/claims | Create Claim
[**deleteClaimV1ClaimsClaimIdDelete**](ClaimsApi.md#deleteClaimV1ClaimsClaimIdDelete) | **DELETE** /v1/claims/{claim_id} | Delete Claim
[**getClaimV1ClaimsClaimIdGet**](ClaimsApi.md#getClaimV1ClaimsClaimIdGet) | **GET** /v1/claims/{claim_id} | Get Claim
[**listClaimsV1ClaimsGet**](ClaimsApi.md#listClaimsV1ClaimsGet) | **GET** /v1/claims | List Claims
[**replaceClaimLinesV1ClaimsClaimIdLinesPut**](ClaimsApi.md#replaceClaimLinesV1ClaimsClaimIdLinesPut) | **PUT** /v1/claims/{claim_id}/lines | Replace Claim Lines
[**updateClaimV1ClaimsClaimIdPatch**](ClaimsApi.md#updateClaimV1ClaimsClaimIdPatch) | **PATCH** /v1/claims/{claim_id} | Update Claim



## createClaimV1ClaimsPost

> ClaimResponse createClaimV1ClaimsPost(claimCreate)

Create Claim

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let claimCreate = new FastApi.ClaimCreate(); // ClaimCreate | 
apiInstance.createClaimV1ClaimsPost(claimCreate).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claimCreate** | [**ClaimCreate**](ClaimCreate.md)|  | 

### Return type

[**ClaimResponse**](ClaimResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## deleteClaimV1ClaimsClaimIdDelete

> deleteClaimV1ClaimsClaimIdDelete(claimId)

Delete Claim

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.deleteClaimV1ClaimsClaimIdDelete(claimId).then(() => {
  console.log('API called successfully.');
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claimId** | **String**|  | 

### Return type

null (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## getClaimV1ClaimsClaimIdGet

> ClaimResponse getClaimV1ClaimsClaimIdGet(claimId)

Get Claim

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.getClaimV1ClaimsClaimIdGet(claimId).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claimId** | **String**|  | 

### Return type

[**ClaimResponse**](ClaimResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## listClaimsV1ClaimsGet

> ClaimListResponse listClaimsV1ClaimsGet(opts)

List Claims

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let opts = {
  'status': new FastApi.ClaimStatus(), // ClaimStatus | 
  'patientId': "patientId_example", // String | 
  'fromDate': new Date("2013-10-20T19:20:30+01:00"), // Date | 
  'toDate': new Date("2013-10-20T19:20:30+01:00"), // Date | 
  'cursor': "cursor_example", // String | 
  'limit': 20 // Number | 
};
apiInstance.listClaimsV1ClaimsGet(opts).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **status** | [**ClaimStatus**](.md)|  | [optional] 
 **patientId** | **String**|  | [optional] 
 **fromDate** | **Date**|  | [optional] 
 **toDate** | **Date**|  | [optional] 
 **cursor** | **String**|  | [optional] 
 **limit** | **Number**|  | [optional] [default to 20]

### Return type

[**ClaimListResponse**](ClaimListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## replaceClaimLinesV1ClaimsClaimIdLinesPut

> [ClaimLineResponse] replaceClaimLinesV1ClaimsClaimIdLinesPut(claimId, claimLineCreate)

Replace Claim Lines

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let claimId = "claimId_example"; // String | 
let claimLineCreate = [new FastApi.ClaimLineCreate()]; // [ClaimLineCreate] | 
apiInstance.replaceClaimLinesV1ClaimsClaimIdLinesPut(claimId, claimLineCreate).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claimId** | **String**|  | 
 **claimLineCreate** | [**[ClaimLineCreate]**](ClaimLineCreate.md)|  | 

### Return type

[**[ClaimLineResponse]**](ClaimLineResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## updateClaimV1ClaimsClaimIdPatch

> ClaimResponse updateClaimV1ClaimsClaimIdPatch(claimId, claimUpdate, opts)

Update Claim

### Example

```javascript
import FastApi from 'fast_api';

let apiInstance = new FastApi.ClaimsApi();
let claimId = "claimId_example"; // String | 
let claimUpdate = new FastApi.ClaimUpdate(); // ClaimUpdate | 
let opts = {
  'ifMatch': "ifMatch_example" // String | 
};
apiInstance.updateClaimV1ClaimsClaimIdPatch(claimId, claimUpdate, opts).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claimId** | **String**|  | 
 **claimUpdate** | [**ClaimUpdate**](ClaimUpdate.md)|  | 
 **ifMatch** | **String**|  | [optional] 

### Return type

[**ClaimResponse**](ClaimResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

