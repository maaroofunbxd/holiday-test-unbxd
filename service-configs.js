// 🔧 Generic URL Builder for K6 Load and Stress Tests
// Works with ANY service - routing info comes from JSONL data (path field)

// 🔧 Generic URL Builder - Works with any service
// All routing information (path, query_string) comes from the JSONL data
export function getUrlBuilder(serviceType) {
  // Completely generic - no service-specific logic needed!
  // The JSONL files contain all routing information in the 'path' field
  return (host, payload) => {
    // Validate required fields
    if (!payload.path) {
      console.warn('⚠️  Missing path field in payload');
      return null;
    }
    
    const method = (payload.type || payload.method || '').toLowerCase();
    let url = `${host}${payload.path}`;
    if (payload.query_string) {
      const queryString = payload.query_string;
      url += queryString.startsWith('?') ? queryString : '?' + queryString;
    }

    if (method === 'get') {
      return { url, method: 'GET', body: null };
    }

    if (method === 'post' || method === 'put' || method === 'patch' || method === 'delete') {
      const body = payload.payload ? JSON.stringify(payload.payload) : null;
      return { url, method: method.toUpperCase(), body };
    }

    return null;
  };
}

