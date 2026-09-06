# DentalClaimsEngine.ClaimsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**createClaimApiV1ClaimsPost**](ClaimsApi.md#createClaimApiV1ClaimsPost) | **POST** /api/v1/claims | Create Claim
[**createClaimV1ClaimsPost**](ClaimsApi.md#createClaimV1ClaimsPost) | **POST** /v1/claims | Create Claim
[**deleteClaimApiV1ClaimsClaimIdDelete**](ClaimsApi.md#deleteClaimApiV1ClaimsClaimIdDelete) | **DELETE** /api/v1/claims/{claim_id} | Delete Claim
[**deleteClaimV1ClaimsClaimIdDelete**](ClaimsApi.md#deleteClaimV1ClaimsClaimIdDelete) | **DELETE** /v1/claims/{claim_id} | Delete Claim
[**getClaimApiV1ClaimsClaimIdGet**](ClaimsApi.md#getClaimApiV1ClaimsClaimIdGet) | **GET** /api/v1/claims/{claim_id} | Get Claim
[**getClaimV1ClaimsClaimIdGet**](ClaimsApi.md#getClaimV1ClaimsClaimIdGet) | **GET** /v1/claims/{claim_id} | Get Claim
[**listClaimsApiV1ClaimsGet**](ClaimsApi.md#listClaimsApiV1ClaimsGet) | **GET** /api/v1/claims | List Claims
[**listClaimsV1ClaimsGet**](ClaimsApi.md#listClaimsV1ClaimsGet) | **GET** /v1/claims | List Claims
[**replaceClaimLinesV1ClaimsClaimIdLinesPut**](ClaimsApi.md#replaceClaimLinesV1ClaimsClaimIdLinesPut) | **PUT** /v1/claims/{claim_id}/lines | Replace Claim Lines
[**scrubClaimApiV1ClaimsClaimIdScrubPost**](ClaimsApi.md#scrubClaimApiV1ClaimsClaimIdScrubPost) | **POST** /api/v1/claims/{claim_id}/scrub | Scrub Claim
[**submitClaimApiV1ClaimsClaimIdSubmitPost**](ClaimsApi.md#submitClaimApiV1ClaimsClaimIdSubmitPost) | **POST** /api/v1/claims/{claim_id}/submit | Submit Claim
[**updateClaimApiV1ClaimsClaimIdPut**](ClaimsApi.md#updateClaimApiV1ClaimsClaimIdPut) | **PUT** /api/v1/claims/{claim_id} | Update Claim
[**updateClaimV1ClaimsClaimIdPatch**](ClaimsApi.md#updateClaimV1ClaimsClaimIdPatch) | **PATCH** /v1/claims/{claim_id} | Update Claim



## createClaimApiV1ClaimsPost

> Object createClaimApiV1ClaimsPost(claimCreate)

Create Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimCreate = new DentalClaimsEngine.ClaimCreate(); // ClaimCreate | 
apiInstance.createClaimApiV1ClaimsPost(claimCreate).then((data) => {
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

**Object**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json


## createClaimV1ClaimsPost

> ClaimResponse createClaimV1ClaimsPost(claimCreate)

Create Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimCreate = new DentalClaimsEngine.ClaimCreate(); // ClaimCreate | 
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


## deleteClaimApiV1ClaimsClaimIdDelete

> deleteClaimApiV1ClaimsClaimIdDelete(claimId)

Delete Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.deleteClaimApiV1ClaimsClaimIdDelete(claimId).then(() => {
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


## deleteClaimV1ClaimsClaimIdDelete

> deleteClaimV1ClaimsClaimIdDelete(claimId)

Delete Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
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


## getClaimApiV1ClaimsClaimIdGet

> Object getClaimApiV1ClaimsClaimIdGet(claimId)

Get Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.getClaimApiV1ClaimsClaimIdGet(claimId).then((data) => {
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

**Object**

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
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
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


## listClaimsApiV1ClaimsGet

> ClaimBoardPage listClaimsApiV1ClaimsGet(opts)

List Claims

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let opts = {
  'cursor': "cursor_example", // String | 
  'limit': 25, // Number | 
  'status': new DentalClaimsEngine.ClaimStatus(), // ClaimStatus | 
  'patientSearch': "patientSearch_example", // String | 
  'payerId': "payerId_example", // String | 
  'serviceDateFrom': new Date("2013-10-20"), // Date | 
  'serviceDateTo': new Date("2013-10-20") // Date | 
};
apiInstance.listClaimsApiV1ClaimsGet(opts).then((data) => {
  console.log('API called successfully. Returned data: ' + data);
}, (error) => {
  console.error(error);
});

```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **cursor** | **String**|  | [optional] 
 **limit** | **Number**|  | [optional] [default to 25]
 **status** | [**ClaimStatus**](.md)|  | [optional] 
 **patientSearch** | **String**|  | [optional] 
 **payerId** | **String**|  | [optional] 
 **serviceDateFrom** | **Date**|  | [optional] 
 **serviceDateTo** | **Date**|  | [optional] 

### Return type

[**ClaimBoardPage**](ClaimBoardPage.md)

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
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let opts = {
  'status': new DentalClaimsEngine.ClaimStatus(), // ClaimStatus | 
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
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
let claimLineCreate = [new DentalClaimsEngine.ClaimLineCreate()]; // [ClaimLineCreate] | 
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


## scrubClaimApiV1ClaimsClaimIdScrubPost

> Object scrubClaimApiV1ClaimsClaimIdScrubPost(claimId)

Scrub Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.scrubClaimApiV1ClaimsClaimIdScrubPost(claimId).then((data) => {
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

**Object**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## submitClaimApiV1ClaimsClaimIdSubmitPost

> Object submitClaimApiV1ClaimsClaimIdSubmitPost(claimId)

Submit Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
apiInstance.submitClaimApiV1ClaimsClaimIdSubmitPost(claimId).then((data) => {
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

**Object**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json


## updateClaimApiV1ClaimsClaimIdPut

> Object updateClaimApiV1ClaimsClaimIdPut(claimId, claimUpdate)

Update Claim

### Example

```javascript
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
let claimUpdate = new DentalClaimsEngine.ClaimUpdate(); // ClaimUpdate | 
apiInstance.updateClaimApiV1ClaimsClaimIdPut(claimId, claimUpdate).then((data) => {
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

### Return type

**Object**

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
import DentalClaimsEngine from 'dental_claims_engine';

let apiInstance = new DentalClaimsEngine.ClaimsApi();
let claimId = "claimId_example"; // String | 
let claimUpdate = new DentalClaimsEngine.ClaimUpdate(); // ClaimUpdate | 
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

