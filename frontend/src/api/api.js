import ClaimsApi from "./generated/src/api/ClaimsApi";
import ApiClient from "./generated/src/ApiClient";

const API_BASE_URL = "http://127.0.0.1:8000";

export function createClaimsApi(accessToken) {
  const apiClient = new ApiClient(API_BASE_URL);

  if (accessToken) {
    apiClient.defaultHeaders = {
      Authorization: `Bearer ${accessToken}`,
    };
  }

  return new ClaimsApi(apiClient);
}

export async function fetchClaims(accessToken, filters = {}) {
  const api = createClaimsApi(accessToken);

  const options = {
    limit: filters.limit ?? 25,
  };

  if (filters.cursor) {
    options.cursor = filters.cursor;
  }

  if (filters.status) {
    options.status = filters.status;
  }

  if (filters.patientSearch) {
    options.patientSearch = filters.patientSearch;
  }

  if (filters.payerId) {
    options.payerId = filters.payerId;
  }

  if (filters.serviceDateFrom) {
    options.serviceDateFrom = new Date(filters.serviceDateFrom);
  }

  if (filters.serviceDateTo) {
    options.serviceDateTo = new Date(filters.serviceDateTo);
  }

  return api.listClaimsApiV1ClaimsGet(options);
}
