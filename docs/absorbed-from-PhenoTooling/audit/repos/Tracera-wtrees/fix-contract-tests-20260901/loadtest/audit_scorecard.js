// Structural Health Check Script
import http from 'k6/http';
import { check, group } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8080';

export const options = {
  vus: 1,
  duration: '10s',
};

export default function () {
  group('Infrastructure Health', () => {
    const healthRes = http.get(`${BASE_URL}/healthz`);
    check(healthRes, {
      'healthz is up': (r) => r.status === 200,
    });

    const readyRes = http.get(`${BASE_URL}/readyz`);
    check(readyRes, {
      'readyz is up': (r) => r.status === 200,
    });
  });

  group('Service Endpoints', () => {
    const metricsRes = http.get(`${BASE_URL}/metrics`);
    check(metricsRes, {
      'metrics available': (r) => r.status === 200,
    });

    const evidenceRes = http.get(`${BASE_URL}/evidence`);
    check(evidenceRes, {
      'evidence service responding': (r) => r.status === 200,
    });

    const sdlcRes = http.get(`${BASE_URL}/sdlc-pm/health`);
    check(sdlcRes, {
      'sdlc-pm responding': (r) => r.status === 200,
    });

    const problemsRes = http.get(`${BASE_URL}/problems/health`);
    check(problemsRes, {
      'problems service responding': (r) => r.status === 200,
    });

    const orgRes = http.get(`${BASE_URL}/org-intel/health`);
    check(orgRes, {
      'org-intel responding': (r) => r.status === 200,
    });
  });

  group('API V1 Health', () => {
    const matrixRes = http.post(`${BASE_URL}/api/v1/coverage-matrix`, '{}', {
      headers: { 'Content-Type': 'application/json' },
    });
    check(matrixRes, {
      'coverage-matrix API responding': (r) => r.status === 200,
    });
  });
}
