#!/usr/bin/env python3
"""
Centralized service endpoint registry for all Unbxd services.
Loads endpoint configurations from service_endpoints.yaml (or .json for backward compatibility).
Used by all extraction scripts to maintain consistency.
"""

import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class ServiceEndpoints:
    """Manages service endpoint configurations."""
    
    def __init__(self, config_file: str = "service_endpoints.yaml"):
        """Initialize with configuration file."""
        self.config_file = Path(config_file)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load endpoint configuration from YAML or JSON file."""
        config_path = self.config_file
        
        # Try relative to script location if not found
        if not config_path.exists():
            config_path = Path(__file__).parent / self.config_file
        
        # Try .yaml, then .json for backward compatibility
        if not config_path.exists():
            if config_path.suffix == '.yaml':
                json_path = config_path.with_suffix('.json')
                if json_path.exists():
                    config_path = json_path
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Endpoint config file not found: {self.config_file}\n"
                f"Looked in: {self.config_file.absolute()} and {config_path}"
            )
        
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    
    def get_path(self, service: str, endpoint: str, sitekey: str) -> Optional[str]:
        """
        Get the full path for a service endpoint.
        
        Args:
            service: Service name (reranker, ner, qcs)
            endpoint: Endpoint name (recommend, tag, category, etc.)
            sitekey: The sitekey to insert into the path
            
        Returns:
            Full path with sitekey substituted, or None if not found
        """
        try:
            path_template = self._config[service]["endpoints"][endpoint]["path"]
            # Handle both {sitekey} and {siteKey} in templates
            return path_template.format(sitekey=sitekey, siteKey=sitekey, site=sitekey, 
                                       vertical=sitekey, dataset=sitekey)
        except (KeyError, TypeError):
            return None
    
    def get_reranker_path(self, api: str, sitekey: str, payload: Optional[dict] = None) -> Optional[str]:
        """
        Get reranker endpoint path, inferring from payload if needed.
        
        Args:
            api: API name (recommend, recommend_v2, rerank)
            sitekey: The sitekey
            payload: Optional payload to infer endpoint from
            
        Returns:
            Full path or None if not found
        """
        # Infer endpoint from payload indicators
        if payload and isinstance(payload, dict):
            for endpoint_name, endpoint_config in self._config["reranker"]["endpoints"].items():
                if "payload_indicators" in endpoint_config:
                    for indicator in endpoint_config["payload_indicators"]:
                        if indicator in payload:
                            api = endpoint_name
                            break
        
        # Get path from config
        path = self.get_path("reranker", api, sitekey)
        
        # Fallback to default if not found
        if not path:
            # Try new format (default_endpoints dict) or old format (default_endpoint string)
            default_endpoints = self._config["reranker"].get("default_endpoints", {})
            if isinstance(default_endpoints, dict):
                default = default_endpoints.get("POST", "recommend_v2")
            else:
                default = self._config["reranker"].get("default_endpoint", "recommend_v2")
            path = self.get_path("reranker", default, sitekey)
        
        return path
    
    def get_ner_path(self, endpoint: str, sitekey: str) -> Optional[str]:
        """Get NER endpoint path."""
        return self.get_path("ner", endpoint, sitekey)
    
    def get_qcs_path(self, endpoint: str, sitekey: str) -> Optional[str]:
        """Get QCS endpoint path."""
        return self.get_path("qcs", endpoint, sitekey)
    
    def get_all_endpoints(self, service: str) -> Dict[str, Dict[str, Any]]:
        """Get all endpoints for a service."""
        try:
            return self._config[service]["endpoints"]
        except KeyError:
            return {}
    
    def list_services(self) -> list:
        """Get list of all configured services."""
        return list(self._config.keys())
    
    def export_to_js(self, output_file: str = "service-endpoints.js"):
        """
        Export configuration to JavaScript for k6 scripts (future use).
        
        Args:
            output_file: Path to output JavaScript file
        """
        js_content = f"""// 🔧 Service Endpoints Configuration
// Auto-generated from service_endpoints.yaml
// DO NOT EDIT MANUALLY - Regenerate by running:
// python3 -c "from service_endpoints import get_endpoints; get_endpoints().export_to_js()"

export const SERVICE_ENDPOINTS = {json.dumps(self._config, indent=2)};

/**
 * Get endpoint path for a service
 * @param {{string}} service - Service name (reranker, ner, qcs)
 * @param {{string}} endpoint - Endpoint name
 * @param {{string}} sitekey - Site key to insert
 * @returns {{string|null}} Full path or null if not found
 */
export function getEndpointPath(service, endpoint, sitekey) {{
  const config = SERVICE_ENDPOINTS[service]?.endpoints[endpoint];
  if (!config) return null;
  return config.path.replace('{{sitekey}}', sitekey).replace('{{siteKey}}', sitekey);
}}

/**
 * Infer reranker endpoint from payload
 * @param {{object}} payload - Request payload
 * @returns {{string}} Endpoint name
 */
export function inferRerankerEndpoint(payload) {{
  const endpoints = SERVICE_ENDPOINTS.reranker?.endpoints || {{}};
  
  // Check for payload indicators
  for (const [endpointName, config] of Object.entries(endpoints)) {{
    if (config.payload_indicators) {{
      for (const indicator of config.payload_indicators) {{
        if (payload[indicator] !== undefined) {{
          return endpointName;
        }}
      }}
    }}
  }}
  
  // Return default (prefer POST)
  const defaults = SERVICE_ENDPOINTS.reranker?.default_endpoints || {{}};
  return defaults.POST || 'recommend_v2';
}}
"""
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            f.write(js_content)
        
        print(f"✅ Exported JavaScript config to {output_path}")


# Singleton instance
_endpoints = None


def get_endpoints() -> ServiceEndpoints:
    """
    Get singleton instance of ServiceEndpoints.
    
    Returns:
        ServiceEndpoints instance
    """
    global _endpoints
    if _endpoints is None:
        _endpoints = ServiceEndpoints()
    return _endpoints


# Convenience functions for backward compatibility
def get_reranker_path(api: str, sitekey: str, payload: Optional[dict] = None) -> Optional[str]:
    """Get reranker endpoint path."""
    return get_endpoints().get_reranker_path(api, sitekey, payload)


def get_ner_path(endpoint: str, sitekey: str) -> Optional[str]:
    """Get NER endpoint path."""
    return get_endpoints().get_ner_path(endpoint, sitekey)


def get_qcs_path(endpoint: str, sitekey: str) -> Optional[str]:
    """Get QCS endpoint path."""
    return get_endpoints().get_qcs_path(endpoint, sitekey)


if __name__ == "__main__":
    # Demo usage
    endpoints = get_endpoints()
    
    print("📋 Available Services:")
    for service in endpoints.list_services():
        print(f"\n  {service}:")
        for endpoint_name, endpoint_config in endpoints.get_all_endpoints(service).items():
            print(f"    - {endpoint_name}: {endpoint_config['path']}")
    
    print("\n🧪 Testing path generation:")
    test_sitekey = "example-com123456"
    
    # Test reranker
    print(f"\n  Reranker recommend_v2: {endpoints.get_reranker_path('recommend_v2', test_sitekey)}")
    print(f"  Reranker rerank: {endpoints.get_reranker_path('rerank', test_sitekey)}")
    
    # Test with payload inference
    rerank_payload = {"rankingContext": {}, "products": []}
    print(f"  Inferred from payload: {endpoints.get_reranker_path('recommend_v2', test_sitekey, rerank_payload)}")
    
    # Test NER
    print(f"\n  NER tag: {endpoints.get_ner_path('tag', test_sitekey)}")
    
    # Test QCS
    print(f"\n  QCS category: {endpoints.get_qcs_path('category', test_sitekey)}")
    
    # Export JS (optional)
    print("\n📦 To export JavaScript config, run:")
    print("  python -c \"from service_endpoints import get_endpoints; get_endpoints().export_to_js()\"")

