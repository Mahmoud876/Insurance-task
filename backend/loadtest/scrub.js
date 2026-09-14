import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const TOKEN = __ENV.TOKEN;
const CLAIM_ID = __ENV.CLAIM_ID || '';

const scrub_duration = new Trend('scrub_duration_ms', true);
const scrub_errors = new Rate('scrub_errors');

function loadClaimPool() {
  if (CLAIM_ID) {
    return [CLAIM_ID];
  }
  try {
    const state = JSON.parse(open('.seed-state.json'));
    if (Array.isArray(state.claim_ids) && state.claim_ids.length > 0) {
      return state.claim_ids;
    }
  } catch (error) {
    // fall through to error below
  }
  throw new Error(
    'No claim pool found: set CLAIM_ID or run `make load-test-seed` to create claims',
  );
}

const CLAIM_POOL = loadClaimPool();

export const options = {
  scenarios: {
    scrub: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 25 },
        { duration: '10s', target: 50 },
        { duration: '40s', target: 50 },
        { duration: '10s', target: 0 },
      ],
      gracefulStop: '5s',
    },
  },
  thresholds: {
    scrub_duration_ms: ['p(95)<300'],
    scrub_errors: ['rate<0.01'],
    http_req_failed: ['rate<0.01'],
  },
};

export function setup() {
  if (!TOKEN) {
    throw new Error('TOKEN env required: run `make load-test-token` and export TOKEN');
  }
  return { baseUrl: BASE_URL, claimPool: CLAIM_POOL };
}

export default function (data) {
  // Spread concurrent users across the seeded claim pool; VUs keep their claim.
  const claimId = data.claimPool[(__VU - 1) % data.claimPool.length];
  const res = http.post(
    `${data.baseUrl}/api/v1/claims/${claimId}/scrub`,
    null,
    {
      headers: { Authorization: `Bearer ${TOKEN}` },
      timeout: '30s',
    },
  );

  scrub_duration.add(res.timings.duration);

  let isScrubbed = false;
  if (res.status === 200) {
    try {
      isScrubbed = JSON.parse(res.body).status === 'SCRUBBED';
    } catch (error) {
      isScrubbed = false;
    }
  }

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'status is SCRUBBED': () => isScrubbed,
  });
  scrub_errors.add(!ok);
}