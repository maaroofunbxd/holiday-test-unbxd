// 🔧 Service Endpoints Configuration
// Auto-generated from service_endpoints.yaml
// DO NOT EDIT MANUALLY - Regenerate by running:
// python3 -c "from service_endpoints import get_endpoints; get_endpoints().export_to_js()"

export const SERVICE_ENDPOINTS = {
  "reranker": {
    "endpoints": {
      "rerank": {
        "path": "/v1.0/sites/{siteKey}/rerank",
        "method": "POST",
        "version": "v1.0",
        "payload_indicators": [
          "rankingContext"
        ]
      },
      "recommend_v2": {
        "path": "/v2.0/sites/{siteKey}/recommend",
        "method": "POST",
        "version": "v2.0"
      },
      "recommend": {
        "path": "/v1.0/sites/{siteKey}/recommend",
        "method": "GET",
        "version": "v1.0"
      },
      "affinity_facet": {
        "path": "/v1.0/sites/{sitekey}/affinity/facet",
        "method": "GET",
        "version": "v1.0"
      },
      "events_post": {
        "path": "/v1.0/sites/{siteKey}/events",
        "method": "POST",
        "version": "v1.0"
      },
      "events": {
        "path": "/v1.0/sites/{siteKey}/events",
        "method": "GET",
        "version": "v1.0"
      },
      "sessions": {
        "path": "/v1.0/sites/{siteKey}/sessions",
        "method": "GET",
        "version": "v1.0"
      },
      "suggestions": {
        "path": "/v1.0/sites/{site}/suggestions",
        "method": "GET",
        "version": "v1.0"
      },
      "suggestions_blacklist": {
        "path": "/v1.0/sites/{site}/suggestions/blacklist",
        "method": "POST",
        "version": "v1.0"
      },
      "suggestions_put": {
        "path": "/v1.0/sites/{site}/suggestions",
        "method": "PUT",
        "version": "v1.0"
      },
      "suggestions_delete": {
        "path": "/v1.0/sites/{site}/suggestions",
        "method": "DELETE",
        "version": "v1.0"
      },
      "recommend_chat_get": {
        "path": "/v1.0/verticals/{vertical}/recommend/chat",
        "method": "GET",
        "version": "v1.0"
      },
      "recommend_chat": {
        "path": "/v1.0/verticals/{vertical}/recommend/chat",
        "method": "POST",
        "version": "v1.0"
      },
      "tag": {
        "path": "/v1.0/verticals/{vertical}/tag",
        "method": "POST",
        "version": "v1.0"
      },
      "cache_post": {
        "path": "/v1.0/datasets/{dataset}/cache",
        "method": "POST",
        "version": "v1.0"
      },
      "cache": {
        "path": "/v1.0/datasets/{dataset}/cache",
        "method": "GET",
        "version": "v1.0"
      },
      "datasets_post": {
        "path": "/v1.0/datasets/{dataset}",
        "method": "POST",
        "version": "v1.0"
      },
      "datasets": {
        "path": "/v1.0/datasets/{dataset}",
        "method": "GET",
        "version": "v1.0"
      }
    },
    "default_endpoints": {
      "POST": "recommend_v2",
      "GET": "recommend"
    }
  },
  "ner": {
    "endpoints": {
      "tag": {
        "path": "/v1.0/sites/{sitekey}/tag",
        "method": "GET",
        "version": "v1.0"
      },
      "dimensions": {
        "path": "/api/v0/sites/{sitekey}/dimensions",
        "method": "GET",
        "version": "v0"
      }
    }
  },
  "qcs": {
    "endpoints": {
      "category": {
        "path": "/v2/sites/{sitekey}/category",
        "method": "GET",
        "version": "v2"
      }
    }
  }
};

/**
 * Get endpoint path for a service
 * @param {string} service - Service name (reranker, ner, qcs)
 * @param {string} endpoint - Endpoint name
 * @param {string} sitekey - Site key to insert
 * @returns {string|null} Full path or null if not found
 */
export function getEndpointPath(service, endpoint, sitekey) {
  const config = SERVICE_ENDPOINTS[service]?.endpoints[endpoint];
  if (!config) return null;
  return config.path.replace('{sitekey}', sitekey).replace('{siteKey}', sitekey);
}

/**
 * Infer reranker endpoint from payload
 * @param {object} payload - Request payload
 * @returns {string} Endpoint name
 */
export function inferRerankerEndpoint(payload) {
  const endpoints = SERVICE_ENDPOINTS.reranker?.endpoints || {};
  
  // Check for payload indicators
  for (const [endpointName, config] of Object.entries(endpoints)) {
    if (config.payload_indicators) {
      for (const indicator of config.payload_indicators) {
        if (payload[indicator] !== undefined) {
          return endpointName;
        }
      }
    }
  }
  
  // Return default (prefer POST)
  const defaults = SERVICE_ENDPOINTS.reranker?.default_endpoints || {};
  return defaults.POST || 'recommend_v2';
}
