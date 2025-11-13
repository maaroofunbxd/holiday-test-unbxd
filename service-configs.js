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
    
    // Handle GET requests with query_string
    if (payload.type === 'get' && payload.query_string) {
      let url = `${host}${payload.path}`;
      const queryString = payload.query_string;
      url += queryString.startsWith('?') ? queryString : '?' + queryString;
      return { url, method: 'GET', body: null };
    }
    
    // Handle POST requests with payload
    if (payload.type === 'post' && payload.payload) {
      const url = `${host}${payload.path}`;
      return { url, method: 'POST', body: JSON.stringify(payload.payload) };
    }
    
    return null;
  };
}

