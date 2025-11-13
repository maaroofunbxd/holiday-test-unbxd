// 🔧 Shared Service Configuration for K6 Load and Stress Tests
// This file contains the service-specific routing logic for all services

export const SERVICE_CONFIGS = {
  reranker: {
    // Complex routing - uses payload structure to determine endpoint
    buildUrl: (host, payload) => {
      const sitekey = payload.sitekey;
      if (!sitekey) return null;

      // Use standardized type field
      if (payload.type === 'get' && payload.query_string) {
        let url = `${host}/v1.0/sites/${sitekey}/recommend`;
        const queryString = payload.query_string;
        url += queryString.startsWith('?') ? queryString : '?' + queryString;
        return { url, method: 'GET', body: null };
      } else if (payload.type === 'post' && payload.payload) {
        if (payload.payload.rankingContext !== undefined) {
          return {
            url: `${host}/v1.0/sites/${sitekey}/rerank`,
            method: 'POST',
            body: JSON.stringify(payload.payload)
          };
        } else {
          return {
            url: `${host}/v2.0/sites/${sitekey}/recommend`,
            method: 'POST',
            body: JSON.stringify(payload.payload)
          };
        }
      }
      return null;
    }
  },
  
  ner: {
    // NER uses GET requests with query strings
    buildUrl: (host, payload) => {
      const sitekey = payload.sitekey;
      if (!sitekey || payload.type !== 'get') return null;
      
      // Use path from payload or construct default
      let url = `${host}${payload.path || `/v1.0/sites/${sitekey}/tag`}`;
      if (payload.query_string) {
        const queryString = payload.query_string;
        url += queryString.startsWith('?') ? queryString : '?' + queryString;
      }
      return { url, method: 'GET', body: null };
    }
  },
  
  qcs: {
    // QCS uses GET requests with query strings
    buildUrl: (host, payload) => {
      const sitekey = payload.sitekey;
      if (!sitekey || payload.type !== 'get') return null;
      
      // Use path from payload
      let url = `${host}${payload.path || `/v2/sites/${sitekey}/category`}`;
      if (payload.query_string) {
        const queryString = payload.query_string;
        url += queryString.startsWith('?') ? queryString : '?' + queryString;
      }
      return { url, method: 'GET', body: null };
    }
  },
};

// 🔧 URL Builder Factory - Supports both predefined and custom services
export function getUrlBuilder(serviceType) {
  // Check if it's a predefined service
  const config = SERVICE_CONFIGS[serviceType];
  
  if (config && config.buildUrl) {
    return config.buildUrl;
  }
  
  // Fallback: Generic builder based on standardized type field
  return (host, payload) => {
    const sitekey = payload.sitekey;
    if (!sitekey) return null;
    
    // Handle GET requests with query_string
    if (payload.type === 'get' && payload.query_string) {
      let url = `${host}${payload.path || '/'}`;
      const queryString = payload.query_string;
      url += queryString.startsWith('?') ? queryString : '?' + queryString;
      return { url, method: 'GET', body: null };
    }
    
    // Handle POST requests with payload
    if (payload.type === 'post' && payload.payload) {
      const url = `${host}${payload.path || '/'}`;
      return { url, method: 'POST', body: JSON.stringify(payload.payload) };
    }
    
    return null;
  };
}

