from mcp.server.fastmcp import FastMCP
import json
import os
import requests
from typing import Dict, List, Any
from datetime import datetime

# Create MCP server
mcp = FastMCP("Rails API Documentation Server")

@mcp.tool()
def analyze_rails_controller(controller_code: str) -> str:
    """
    Analyze Rails controller code and extract API endpoint information.
    
    This tool provides the template structure for Cursor to follow when analyzing Rails controllers.
    For accurate route detection, Cursor should also read the rails://routes resource.
    
    WORKFLOW:
    1. Read rails://routes resource to get exact route definitions
    2. Parse routes.rb to find routes for this specific controller
    3. Use real HTTP methods and paths from routes.rb
    4. Analyze controller code using exact routes (not assumptions)
    5. Return JSON following the structure below
    6. Use preview_postman_changes first to see what will be updated
    
    Parameters:
        controller_code: Raw Rails controller code as string
    
    Returns:
        JSON string with suggested API documentation structure
    """
    
    rails_project_path = os.getenv('RAILS_PROJECT_PATH')
    
    suggested_structure = {
        "endpoints": [
            {
                "method": "GET|POST|PUT|DELETE|PATCH",
                "path": "/api/exact/path/from/routes.rb",
                "controller": "Exact::Controller::Name", 
                "action": "exact_action_name",
                "description": "What this endpoint does based on controller code",
                "parameters": [
                    {
                        "name": "param_name",
                        "type": "string|integer|boolean|array|object",
                        "required": True,
                        "location": "query|body|path|header",
                        "description": "Parameter description from controller code"
                    }
                ],
                "responses": [
                    {
                        "status": 200,
                        "description": "Success response description",
                        "example": {"key": "value"}
                    },
                    {
                        "status": 422,
                        "description": "Error response description", 
                        "example": {"error": "validation failed"}
                    }
                ]
            }
        ]
    }
    
    return json.dumps(suggested_structure, indent=2)

@mcp.resource("rails://routes")
def rails_routes_resource() -> str:
    """
    Provides Rails routes.rb file content from configured Rails project.
    
    Requires RAILS_PROJECT_PATH environment variable to be set.
    """
    rails_project_path = os.getenv('RAILS_PROJECT_PATH')
    
    if not rails_project_path:
        return """
        Error: RAILS_PROJECT_PATH environment variable not set.
        
        Please add to your MCP configuration:
        "env": {
          "RAILS_PROJECT_PATH": "/path/to/your/rails/app"
        }
        """
    
    routes_file = os.path.join(rails_project_path, "config", "routes.rb")
    
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: routes.rb not found at {routes_file}"
    except Exception as e:
        return f"Error reading routes.rb: {str(e)}"

@mcp.tool()
def preview_postman_changes(
    api_data,
    collection_uid: str = None,
    postman_api_key: str = None
) -> str:
    """
    Preview what changes will be made to Postman collection WITHOUT actually updating.
    Shows detailed diff of new vs existing documentation.
    
    Parameters:
        api_data: New API endpoint information (JSON string or dict object)
        collection_uid: Optional override for POSTMAN_COLLECTION_UID  
        postman_api_key: Optional override for POSTMAN_API_KEY
    
    Returns:
        Detailed diff showing what will be added/changed/preserved
    """
    try:
        # Get credentials
        collection_uid = collection_uid or os.getenv('POSTMAN_COLLECTION_UID')
        postman_api_key = postman_api_key or os.getenv('POSTMAN_API_KEY')
        
        if not collection_uid or not postman_api_key:
            return "Error: Missing Postman credentials. Check POSTMAN_COLLECTION_UID and POSTMAN_API_KEY environment variables."
        
        # Handle input data
        if isinstance(api_data, str):
            endpoints_data = json.loads(api_data)
        elif isinstance(api_data, dict):
            endpoints_data = api_data
        else:
            return f"Error: Invalid api_data format"
        
        # Get existing collection
        existing_collection = get_postman_collection(collection_uid, postman_api_key)
        existing_items = existing_collection.get("collection", {}).get("item", [])
        
        # Analyze changes
        changes = analyze_postman_changes(existing_items, endpoints_data)
        
        return format_change_preview(changes)
        
    except json.JSONDecodeError as e:
        return f"Error parsing API data: {str(e)}"
    except Exception as e:
        return f"Error previewing changes: {str(e)}"

@mcp.tool()
def smart_update_postman_collection(
    api_data,
    collection_uid: str = None,
    postman_api_key: str = None,
    include_documentation: bool = True,
    preserve_existing_docs: bool = True
) -> str:
    """
    Intelligently update Postman collection - automatically detects if endpoints exist and either adds new or updates existing.
    Optionally adds documentation to collection and individual requests with smart preservation.
    
    Requires these environment variables:
    - POSTMAN_COLLECTION_UID: Your Postman collection UID
    - POSTMAN_API_KEY: Your Postman API key  
    - RAILS_PROJECT_PATH: Path to your Rails application
    
    Parameters:
        api_data: API endpoint information (JSON string or dict object)
        collection_uid: Optional override for POSTMAN_COLLECTION_UID
        postman_api_key: Optional override for POSTMAN_API_KEY
        include_documentation: Whether to add documentation to collection and requests (default: True)
        preserve_existing_docs: If True, preserves existing documentation and only adds new info (default: True)
    
    Returns:
        Detailed status message about what was added/updated
    """
    try:
        # Get credentials from environment variables if not provided
        collection_uid = collection_uid or os.getenv('POSTMAN_COLLECTION_UID')
        postman_api_key = postman_api_key or os.getenv('POSTMAN_API_KEY')
        
        if not collection_uid:
            return "Error: Postman collection UID not provided. Set POSTMAN_COLLECTION_UID environment variable or pass collection_uid parameter."
        
        if not postman_api_key:
            return "Error: Postman API key not provided. Set POSTMAN_API_KEY environment variable or pass postman_api_key parameter."
        
        # Handle both string and dict input
        if isinstance(api_data, str):
            endpoints_data = json.loads(api_data)
        elif isinstance(api_data, dict):
            endpoints_data = api_data
        else:
            return f"Error: api_data must be a JSON string or dict object, got {type(api_data)}"
        
        # Get existing collection
        existing_collection = get_postman_collection(collection_uid, postman_api_key)
        existing_items = existing_collection.get("collection", {}).get("item", [])
        
        # Generate collection documentation if requested
        if include_documentation:
            collection_description = generate_collection_description(endpoints_data)
            # Preserve existing description if preserve_existing_docs is True
            if preserve_existing_docs:
                existing_desc = existing_collection.get("collection", {}).get("info", {}).get("description", "")
                if existing_desc:
                    collection_description = merge_descriptions(existing_desc, collection_description)
            existing_collection["collection"]["info"]["description"] = collection_description
        
        # Create lookup for existing endpoints
        existing_lookup = {}
        for item in existing_items:
            if "request" in item:
                method = item["request"].get("method", "GET")
                url = item["request"].get("url", {})
                clean_path = extract_clean_path_from_postman_url(url)
                key = f"{method}:{clean_path}"
                existing_lookup[key] = item
        
        # Process new endpoints
        new_endpoints = []
        updated_endpoints = []
        unchanged_endpoints = []
        
        for endpoint in endpoints_data.get("endpoints", []):
            method = endpoint.get("method", "GET")
            raw_path = endpoint.get("path", "")
            clean_path = extract_clean_path_from_string(raw_path)
            key = f"{method}:{clean_path}"
            
            # Convert endpoint to Postman format
            new_item = convert_endpoint_to_postman_item(endpoint, include_documentation)
            
            if key in existing_lookup:
                existing_item = existing_lookup[key]
                
                # Merge with preservation if enabled
                if preserve_existing_docs:
                    merged_item = merge_postman_items_with_preservation(existing_item, new_item)
                else:
                    merged_item = new_item
                
                # Check if anything actually changed
                if items_are_different(existing_item, merged_item):
                    existing_lookup[key] = merged_item
                    updated_endpoints.append(f"{method} {clean_path}")
                else:
                    unchanged_endpoints.append(f"{method} {clean_path}")
            else:
                # New endpoint
                existing_lookup[key] = new_item
                new_endpoints.append(f"{method} {clean_path}")
        
        # Update collection with all items
        existing_collection["collection"]["item"] = list(existing_lookup.values())
        
        # Send update to Postman
        update_postman_via_api(collection_uid, existing_collection, postman_api_key)
        
        # Create status message
        status_parts = []
        if new_endpoints:
            status_parts.append(f"✅ Added {len(new_endpoints)} new endpoint(s): {', '.join(new_endpoints)}")
        if updated_endpoints:
            status_parts.append(f"🔄 Updated {len(updated_endpoints)} existing endpoint(s): {', '.join(updated_endpoints)}")
        if unchanged_endpoints:
            status_parts.append(f"⚪ {len(unchanged_endpoints)} endpoint(s) unchanged: {', '.join(unchanged_endpoints)}")
        if include_documentation:
            preservation_note = " (with documentation preservation)" if preserve_existing_docs else ""
            status_parts.append(f"📚 Documentation added to collection and individual requests{preservation_note}")
        
        if not status_parts:
            return "No endpoints found in the provided data."
        
        return "\n".join(status_parts) + f"\n\n📋 Collection UID: {collection_uid}"
        
    except json.JSONDecodeError as e:
        return f"Error parsing API data: {str(e)}"
    except Exception as e:
        return f"Error updating Postman collection: {str(e)}"

@mcp.tool()
def generate_api_documentation(
    api_data,
    format_type: str = "markdown",
    template_style: str = "detailed"
) -> str:
    """
    Generate API documentation from Rails endpoint data.
    
    Parameters:
        api_data: API endpoint information (JSON string or dict object)
        format_type: "markdown" or "json"
        template_style: "detailed" or "compact" (only for markdown)
    
    Returns:
        Generated API documentation as string
    """
    try:
        # Handle both string and dict input
        if isinstance(api_data, str):
            endpoints_data = json.loads(api_data)
        elif isinstance(api_data, dict):
            endpoints_data = api_data
        else:
            return f"Error: api_data must be a JSON string or dict object, got {type(api_data)}"
        
        if format_type == "markdown":
            return generate_markdown_docs(endpoints_data, template_style)
        elif format_type == "json":
            return json.dumps(endpoints_data, indent=2)
        else:
            return f"Error: Unsupported format_type '{format_type}'. Use 'markdown' or 'json'."
            
    except json.JSONDecodeError as e:
        return f"Error parsing API data: {str(e)}"
    except Exception as e:
        return f"Error generating documentation: {str(e)}"

@mcp.tool()
def check_postman_connection() -> str:
    """
    Check if Postman API connection is working with current environment variables.
    
    Returns:
        Status message about the connection
    """
    try:
        collection_uid = os.getenv('POSTMAN_COLLECTION_UID')
        postman_api_key = os.getenv('POSTMAN_API_KEY')
        rails_project_path = os.getenv('RAILS_PROJECT_PATH')
        
        status = []
        
        if not collection_uid:
            status.append("❌ POSTMAN_COLLECTION_UID environment variable not set")
        else:
            status.append(f"✅ POSTMAN_COLLECTION_UID: {collection_uid}")
        
        if not postman_api_key:
            status.append("❌ POSTMAN_API_KEY environment variable not set")
        else:
            status.append("✅ POSTMAN_API_KEY: Set")
        
        if not rails_project_path:
            status.append("❌ RAILS_PROJECT_PATH environment variable not set")
        else:
            status.append(f"✅ RAILS_PROJECT_PATH: {rails_project_path}")
            
            # Check if routes.rb exists
            routes_file = os.path.join(rails_project_path, "config", "routes.rb")
            if os.path.exists(routes_file):
                status.append(f"✅ routes.rb found at: {routes_file}")
            else:
                status.append(f"❌ routes.rb not found at: {routes_file}")
        
        # Test Postman connection if both credentials available
        if collection_uid and postman_api_key:
            headers = {"X-API-Key": postman_api_key}
            response = requests.get(
                f"https://api.getpostman.com/collections/{collection_uid}",
                headers=headers
            )
            
            if response.status_code == 200:
                collection_data = response.json()
                collection_name = collection_data.get("collection", {}).get("info", {}).get("name", "Unknown")
                status.append(f"✅ Successfully connected to Postman collection: '{collection_name}'")
            elif response.status_code == 401:
                status.append("❌ Invalid Postman API key")
            elif response.status_code == 404:
                status.append(f"❌ Collection not found (UID: {collection_uid})")
            else:
                status.append(f"❌ Error connecting to Postman API: {response.status_code}")
        
        return "\n".join(status)
            
    except Exception as e:
        return f"❌ Error checking connections: {str(e)}"

# Helper Functions
def get_postman_collection(collection_uid: str, api_key: str) -> Dict:
    """Fetch existing Postman collection"""
    headers = {"X-API-Key": api_key}
    response = requests.get(
        f"https://api.getpostman.com/collections/{collection_uid}",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def update_postman_via_api(collection_uid: str, collection_data: Dict, api_key: str) -> str:
    """Update Postman collection via API"""
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    response = requests.put(
        f"https://api.getpostman.com/collections/{collection_uid}",
        headers=headers,
        json=collection_data
    )
    response.raise_for_status()
    return "Successfully updated via Postman API"

def extract_clean_path_from_postman_url(url_obj) -> str:
    """Extract clean path from Postman URL object"""
    if isinstance(url_obj, dict):
        if "path" in url_obj and isinstance(url_obj["path"], list):
            clean_path = "/" + "/".join(url_obj["path"])
            return remove_format_extension(clean_path)
        if "raw" in url_obj:
            return extract_clean_path_from_string(url_obj["raw"])
    return extract_clean_path_from_string(str(url_obj))

def extract_clean_path_from_string(url_string: str) -> str:
    """Extract clean path from URL string, removing query parameters and format extensions"""
    from urllib.parse import urlparse
    
    if url_string.startswith('http'):
        parsed = urlparse(url_string)
        clean_path = parsed.path
    else:
        if '?' in url_string:
            clean_path = url_string.split('?')[0]
        else:
            clean_path = url_string
    
    return remove_format_extension(clean_path)

def remove_format_extension(path: str) -> str:
    """Remove Rails format extensions like .json, .xml, .html from path"""
    format_extensions = ['.json', '.xml', '.html', '.csv', '.pdf', '.txt']
    
    for ext in format_extensions:
        if path.endswith(ext):
            return path[:-len(ext)]
    
    return path

def convert_endpoint_to_postman_item(endpoint: Dict, include_documentation: bool = False) -> Dict:
    """Convert single endpoint to Postman item format following official Postman collection structure"""
    method = endpoint.get("method", "GET")
    raw_path = endpoint.get("path", "")
    clean_path = extract_clean_path_from_string(raw_path)
    description = endpoint.get("description", "")
    parameters = endpoint.get("parameters", [])
    
    # Separate parameters by location
    query_params = [p for p in parameters if p.get("location") == "query"]
    body_params = [p for p in parameters if p.get("location") == "body"]
    header_params = [p for p in parameters if p.get("location") == "header"]
    form_params = [p for p in parameters if p.get("location") == "form"]
    
    # Build headers array
    headers = []
    
    # Add headers from parameters
    for param in header_params:
        headers.append({
            "key": param.get("name", ""),
            "value": "",
            "description": param.get("description", "")
        })
    
    # Add Content-Type header based on body type
    if body_params or form_params:
        if form_params:
            headers.append({
                "key": "Content-Type",
                "value": "application/x-www-form-urlencoded"
            })
        else:
            headers.append({
                "key": "Content-Type", 
                "value": "application/json"
            })
    
    # Build URL object with query parameters
    url_object = {
        "raw": clean_path,
        "path": [p for p in clean_path.split("/") if p]
    }
    
    # Add query parameters to URL object
    if query_params:
        url_object["query"] = []
        for param in query_params:
            url_object["query"].append({
                "key": param.get("name", ""),
                "value": param.get("default", ""),
                "disabled": False,
                "description": param.get("description", "")
            })
    
    # Build request object
    postman_item = {
        "name": f"{method} {clean_path}",
        "request": {
            "method": method,
            "header": headers,
            "url": url_object
        }
    }
    
    # Add description
    if include_documentation:
        postman_item["request"]["description"] = generate_request_documentation(endpoint)
    elif description:
        postman_item["request"]["description"] = description
    
    # Build body object if there are body/form parameters
    if body_params or form_params:
        if form_params:
            # Form data body
            postman_item["request"]["body"] = {
                "mode": "urlencoded",
                "urlencoded": []
            }
            for param in form_params:
                postman_item["request"]["body"]["urlencoded"].append({
                    "key": param.get("name", ""),
                    "value": param.get("default", ""),
                    "disabled": False,
                    "description": param.get("description", "")
                })
        else:
            # JSON body
            body_object = {}
            for param in body_params:
                param_name = param.get("name", "")
                param_type = param.get("type", "string")
                
                if param_type == "string":
                    body_object[param_name] = param.get("default", "")
                elif param_type == "integer":
                    body_object[param_name] = param.get("default", 0)
                elif param_type == "boolean":
                    body_object[param_name] = param.get("default", False)
                elif param_type == "array":
                    body_object[param_name] = param.get("default", [])
                elif param_type == "object":
                    body_object[param_name] = param.get("default", {})
                else:
                    body_object[param_name] = param.get("default", "")
            
            postman_item["request"]["body"] = {
                "mode": "raw",
                "raw": json.dumps(body_object, indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
    
    return postman_item

def analyze_postman_changes(existing_items: List[Dict], new_endpoints_data: Dict) -> Dict:
    """Analyze what changes would be made"""
    
    # Create lookup for existing endpoints
    existing_lookup = {}
    for item in existing_items:
        if "request" in item:
            method = item["request"].get("method", "GET")
            url = item["request"].get("url", {})
            clean_path = extract_clean_path_from_postman_url(url)
            key = f"{method}:{clean_path}"
            existing_lookup[key] = item
    
    changes = {
        "new_endpoints": [],
        "updated_endpoints": [],
        "unchanged_endpoints": [],
        "documentation_changes": []
    }
    
    for endpoint in new_endpoints_data.get("endpoints", []):
        method = endpoint.get("method", "GET")
        raw_path = endpoint.get("path", "")
        clean_path = extract_clean_path_from_string(raw_path)
        key = f"{method}:{clean_path}"
        
        if key in existing_lookup:
            # Existing endpoint - analyze what would change
            existing_item = existing_lookup[key]
            new_item = convert_endpoint_to_postman_item(endpoint, True)
            
            endpoint_changes = compare_postman_items(existing_item, new_item)
            
            if endpoint_changes["has_changes"]:
                changes["updated_endpoints"].append({
                    "endpoint": f"{method} {clean_path}",
                    "changes": endpoint_changes
                })
            else:
                changes["unchanged_endpoints"].append(f"{method} {clean_path}")
        else:
            # New endpoint
            changes["new_endpoints"].append(f"{method} {clean_path}")
    
    return changes

def compare_postman_items(existing: Dict, new: Dict) -> Dict:
    """Compare two Postman items and return detailed changes"""
    
    changes = {
        "has_changes": False,
        "request_changes": {},
        "documentation_changes": {}
    }
    
    # Compare request structure (headers, URL, body)
    existing_request = existing.get("request", {})
    new_request = new.get("request", {})
    
    # Compare headers
    existing_headers = existing_request.get("header", [])
    new_headers = new_request.get("header", [])
    
    if headers_different(existing_headers, new_headers):
        changes["has_changes"] = True
        changes["request_changes"]["headers"] = {
            "existing": len(existing_headers),
            "new": len(new_headers),
            "action": "headers_updated"
        }
    
    # Compare URL parameters
    existing_url = existing_request.get("url", {})
    new_url = new_request.get("url", {})
    
    if url_different(existing_url, new_url):
        changes["has_changes"] = True
        changes["request_changes"]["url"] = {
            "action": "url_parameters_updated"
        }
    
    # Compare body
    existing_body = existing_request.get("body")
    new_body = new_request.get("body")
    
    if body_different(existing_body, new_body):
        changes["has_changes"] = True
        changes["request_changes"]["body"] = {
            "action": "request_body_updated"
        }
    
    # Compare documentation
    existing_desc = existing_request.get("description", "")
    new_desc = new_request.get("description", "")
    
    if existing_desc != new_desc:
        changes["has_changes"] = True
        changes["documentation_changes"]["description"] = {
            "existing_length": len(existing_desc),
            "new_length": len(new_desc),
            "action": "documentation_updated"
        }
    
    return changes

def headers_different(existing: List, new: List) -> bool:
    """Compare header arrays"""
    if len(existing) != len(new):
        return True
    
    existing_keys = {h.get("key", "") for h in existing}
    new_keys = {h.get("key", "") for h in new}
    
    return existing_keys != new_keys

def url_different(existing: Dict, new: Dict) -> bool:
    """Compare URL objects"""
    existing_query = existing.get("query", [])
    new_query = new.get("query", [])
    
    if len(existing_query) != len(new_query):
        return True
    
    existing_params = {q.get("key", "") for q in existing_query}
    new_params = {q.get("key", "") for q in new_query}
    
    return existing_params != new_params

def body_different(existing: Dict, new: Dict) -> bool:
    """Compare body objects"""
    if not existing and not new:
        return False
    if not existing or not new:
        return True
    
    existing_mode = existing.get("mode", "")
    new_mode = new.get("mode", "")
    
    return existing_mode != new_mode

def items_are_different(existing: Dict, new: Dict) -> bool:
    """Check if two Postman items are actually different"""
    changes = compare_postman_items(existing, new)
    return changes["has_changes"]

def merge_postman_items_with_preservation(existing: Dict, new: Dict) -> Dict:
    """Merge new item data with existing while preserving existing documentation"""
    merged = new.copy()
    
    # Use smart description merging for request documentation
    existing_desc = existing.get("request", {}).get("description", "")
    new_desc = new.get("request", {}).get("description", "")
    
    if existing_desc or new_desc:
        merged["request"]["description"] = merge_request_descriptions(existing_desc, new_desc)
    
    return merged

def merge_descriptions(existing: str, new: str) -> str:
    """Merge existing and new descriptions intelligently with auto-generated content detection"""
    if not existing:
        return new
    if not new:
        return existing
    if existing == new:
        return existing
    
    # Check if existing content has auto-generated markers
    if "<!-- AUTO-GENERATED START -->" in existing and "<!-- AUTO-GENERATED END -->" in existing:
        # Extract manual content (before and after auto-generated section)
        parts = existing.split("<!-- AUTO-GENERATED START -->")
        manual_before = parts[0].strip() if parts[0].strip() else ""
        
        if "<!-- AUTO-GENERATED END -->" in existing:
            auto_and_after = existing.split("<!-- AUTO-GENERATED END -->", 1)
            manual_after = auto_and_after[1].strip() if len(auto_and_after) > 1 and auto_and_after[1].strip() else ""
        else:
            manual_after = ""
        
        # Rebuild with preserved manual content + new auto-generated content
        result = ""
        if manual_before:
            result += manual_before + "\n\n"
        result += new
        if manual_after:
            result += "\n\n" + manual_after
        
        return result
    
    # If no auto-generated markers, check if existing looks like old auto-generated content
    elif (existing.startswith("# API Collection Documentation") or 
          "This collection contains" in existing or
          "Auto-generated on" in existing):
        # Likely old auto-generated content without markers - replace it
        return new
    
    # Otherwise, preserve existing and append new (manual content)
    return f"{existing}\n\n---\n\n{new}"

def format_change_preview(changes: Dict) -> str:
    """Format changes into readable preview"""
    
    preview = "# 📋 Postman Collection Update Preview\n\n"
    
    # New endpoints
    if changes["new_endpoints"]:
        preview += "## ✅ New Endpoints (Will be added)\n\n"
        for endpoint in changes["new_endpoints"]:
            preview += f"- **{endpoint}** (New endpoint with full documentation)\n"
        preview += "\n"
    
    # Updated endpoints
    if changes["updated_endpoints"]:
        preview += "## 🔄 Updated Endpoints (Will be modified)\n\n"
        for update in changes["updated_endpoints"]:
            endpoint = update["endpoint"]
            endpoint_changes = update["changes"]
            
            preview += f"### {endpoint}\n\n"
            
            # Show specific changes
            if endpoint_changes["request_changes"]:
                preview += "**Request Changes:**\n"
                for change_type, change_data in endpoint_changes["request_changes"].items():
                    action = change_data["action"]
                    preview += f"- {action.replace('_', ' ').title()}\n"
            
            if endpoint_changes["documentation_changes"]:
                preview += "**Documentation Changes:**\n"
                for change_type, change_data in endpoint_changes["documentation_changes"].items():
                    existing_len = change_data.get("existing_length", 0)
                    new_len = change_data.get("new_length", 0)
                    
                    if existing_len == 0:
                        preview += f"- Documentation will be added ({new_len} characters)\n"
                    elif new_len > existing_len:
                        preview += f"- Documentation will be enhanced ({existing_len} → {new_len} characters)\n"
                    else:
                        preview += f"- Documentation will be updated ({existing_len} → {new_len} characters)\n"
            
            preview += "\n"
    
    # Unchanged endpoints
    if changes["unchanged_endpoints"]:
        preview += "## ⚪ Unchanged Endpoints (Will remain as-is)\n\n"
        for endpoint in changes["unchanged_endpoints"]:
            preview += f"- **{endpoint}** (No changes detected)\n"
        preview += "\n"
    
    # Summary
    total_changes = len(changes["new_endpoints"]) + len(changes["updated_endpoints"])
    if total_changes == 0:
        preview += "## 🎉 Summary\n\nNo changes detected. Your Postman collection is already up to date!\n"
    else:
        preview += f"## 📊 Summary\n\n"
        preview += f"- **{len(changes['new_endpoints'])}** new endpoints\n"
        preview += f"- **{len(changes['updated_endpoints'])}** updated endpoints\n" 
        preview += f"- **{len(changes['unchanged_endpoints'])}** unchanged endpoints\n\n"
        preview += "**Next Steps:**\n"
        preview += "- Review the changes above\n"
        preview += "- If you approve, use smart_update_postman_collection to apply changes\n"
        preview += "- If you want to modify something, update your controller and preview again\n"
        preview += "\n**Note:** Documentation preservation is enabled by default to protect existing content.\n"
    
    return preview

def generate_collection_description(endpoints_data: Dict) -> str:
    """Generate overall collection description for Postman"""
    endpoints = endpoints_data.get("endpoints", [])
    
    if not endpoints:
        return "API Documentation - No endpoints available"
    
    # Add markers for auto-generated content detection
    description = "<!-- AUTO-GENERATED START -->\n"
    description += "# API Collection Documentation\n\n"
    description += f"This collection contains {len(endpoints)} API endpoint(s):\n\n"
    
    for endpoint in endpoints:
        method = endpoint.get("method", "GET")
        path = extract_clean_path_from_string(endpoint.get("path", ""))
        desc = endpoint.get("description", "")
        
        description += f"- **{method} {path}**"
        if desc:
            first_sentence = desc.split('.')[0] + '.' if '.' in desc else desc
            description += f" - {first_sentence}"
        description += "\n"
    
    description += f"\n*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    description += "<!-- AUTO-GENERATED END -->"
    return description

def generate_request_documentation(endpoint: Dict) -> str:
    """Generate detailed documentation for individual request in Postman"""
    method = endpoint.get("method", "GET")
    path = extract_clean_path_from_string(endpoint.get("path", ""))
    description = endpoint.get("description", "")
    controller = endpoint.get("controller", "")
    action = endpoint.get("action", "")
    parameters = endpoint.get("parameters", [])
    responses = endpoint.get("responses", [])
    
    # Add markers for auto-generated content detection
    doc = "<!-- AUTO-GENERATED-REQUEST START -->\n"
    doc += f"# {method} {path}\n\n"
    
    if description:
        doc += f"{description}\n\n"
    
    if controller and action:
        doc += f"**Controller:** `{controller}#{action}`\n\n"
    
    # Parameters documentation
    if parameters:
        query_params = [p for p in parameters if p.get("location") == "query"]
        path_params = [p for p in parameters if p.get("location") == "path"]
        header_params = [p for p in parameters if p.get("location") == "header"]
        body_params = [p for p in parameters if p.get("location") == "body"]
        form_params = [p for p in parameters if p.get("location") == "form"]
        
        if query_params:
            doc += "## Query Parameters\n\n"
            for param in query_params:
                name = param.get("name", "")
                param_type = param.get("type", "string")
                required = "Required" if param.get("required", False) else "Optional"
                param_desc = param.get("description", "")
                doc += f"- **{name}** ({param_type}, {required}): {param_desc}\n"
            doc += "\n"
        
        if path_params:
            doc += "## Path Parameters\n\n"
            for param in path_params:
                name = param.get("name", "")
                param_type = param.get("type", "string")
                param_desc = param.get("description", "")
                doc += f"- **{name}** ({param_type}): {param_desc}\n"
            doc += "\n"
        
        if header_params:
            doc += "## Headers\n\n"
            for param in header_params:
                name = param.get("name", "")
                param_desc = param.get("description", "")
                doc += f"- **{name}**: {param_desc}\n"
            doc += "\n"
        
        if body_params or form_params:
            doc += "## Request Body\n\n"
            target_params = body_params if body_params else form_params
            content_type = "application/json" if body_params else "application/x-www-form-urlencoded"
            doc += f"**Content-Type:** `{content_type}`\n\n"
            for param in target_params:
                name = param.get("name", "")
                param_type = param.get("type", "string")
                required = "Required" if param.get("required", False) else "Optional"
                param_desc = param.get("description", "")
                doc += f"- **{name}** ({param_type}, {required}): {param_desc}\n"
            doc += "\n"
    
    # Response documentation
    if responses:
        doc += "## Responses\n\n"
        for response in responses:
            status = response.get("status", 200)
            resp_desc = response.get("description", "")
            example = response.get("example", {})
            
            doc += f"### {status} - {resp_desc}\n\n"
            if example:
                doc += "```json\n"
                doc += json.dumps(example, indent=2)
                doc += "\n```\n\n"
    
    doc += "<!-- AUTO-GENERATED-REQUEST END -->"
    return doc

def merge_request_descriptions(existing: str, new: str) -> str:
    """Merge existing and new request descriptions intelligently with auto-generated content detection"""
    if not existing:
        return new
    if not new:
        return existing
    if existing == new:
        return existing
    
    # Check if existing content has auto-generated markers
    if "<!-- AUTO-GENERATED-REQUEST START -->" in existing and "<!-- AUTO-GENERATED-REQUEST END -->" in existing:
        # Extract manual content (before and after auto-generated section)
        parts = existing.split("<!-- AUTO-GENERATED-REQUEST START -->")
        manual_before = parts[0].strip() if parts[0].strip() else ""
        
        if "<!-- AUTO-GENERATED-REQUEST END -->" in existing:
            auto_and_after = existing.split("<!-- AUTO-GENERATED-REQUEST END -->", 1)
            manual_after = auto_and_after[1].strip() if len(auto_and_after) > 1 and auto_and_after[1].strip() else ""
        else:
            manual_after = ""
        
        # Rebuild with preserved manual content + new auto-generated content
        result = ""
        if manual_before:
            result += manual_before + "\n\n"
        result += new
        if manual_after:
            result += "\n\n" + manual_after
        
        return result
    
    # If no auto-generated markers, check if existing looks like old auto-generated content
    elif (existing.startswith("# GET ") or existing.startswith("# POST ") or 
          existing.startswith("# PUT ") or existing.startswith("# DELETE ") or
          "## Query Parameters" in existing or
          "## Request Body" in existing or
          "## Responses" in existing or
          "**Controller:**" in existing):
        # Likely old auto-generated content without markers - replace it
        return new
    
    # Otherwise, preserve existing and append new (manual content)
    return f"{existing}\n\n---\n\n{new}"

def generate_markdown_docs(endpoints_data: Dict, style: str) -> str:
    """Generate Markdown documentation based on style"""
    endpoints = endpoints_data.get("endpoints", [])
    
    if not endpoints:
        return "# API Documentation\n\nNo endpoints found in the provided data.\n"
    
    if style == "detailed":
        return generate_detailed_markdown(endpoints)
    elif style == "compact":
        return generate_compact_markdown(endpoints)
    else:
        return generate_detailed_markdown(endpoints)

def generate_detailed_markdown(endpoints: List[Dict]) -> str:
    """Generate detailed Markdown documentation with proper formatting"""
    doc = "# API Documentation\n\n"
    doc += "This documentation was auto-generated from Rails controller analysis.\n\n"
    doc += "---\n\n"
    
    for i, endpoint in enumerate(endpoints, 1):
        method = endpoint.get("method", "GET")
        raw_path = endpoint.get("path", "")
        clean_path = extract_clean_path_from_string(raw_path)
        description = endpoint.get("description", "")
        controller = endpoint.get("controller", "")
        action = endpoint.get("action", "")
        
        # Endpoint header
        doc += f"## {i}. {method} {clean_path}\n\n"
        
        if description:
            doc += f"**Description:** {description}\n\n"
        
        if controller and action:
            doc += f"**Controller:** `{controller}#{action}`\n\n"
        
        # Parameters section
        parameters = endpoint.get("parameters", [])
        if parameters:
            doc += "### Parameters\n\n"
            
            # Group parameters by location
            query_params = [p for p in parameters if p.get("location") == "query"]
            path_params = [p for p in parameters if p.get("location") == "path"]
            header_params = [p for p in parameters if p.get("location") == "header"]
            body_params = [p for p in parameters if p.get("location") == "body"]
            form_params = [p for p in parameters if p.get("location") == "form"]
            
            if query_params:
                doc += "#### Query Parameters\n\n"
                doc += "| Name | Type | Required | Description |\n"
                doc += "|------|------|----------|-------------|\n"
                for param in query_params:
                    name = param.get("name", "")
                    param_type = param.get("type", "string")
                    required = "✅ Yes" if param.get("required", False) else "❌ No"
                    param_desc = param.get("description", "No description provided")
                    doc += f"| `{name}` | `{param_type}` | {required} | {param_desc} |\n"
                doc += "\n"
            
            if path_params:
                doc += "#### Path Parameters\n\n"
                doc += "| Name | Type | Required | Description |\n"
                doc += "|------|------|----------|-------------|\n"
                for param in path_params:
                    name = param.get("name", "")
                    param_type = param.get("type", "string")
                    required = "✅ Yes" if param.get("required", False) else "❌ No"
                    param_desc = param.get("description", "No description provided")
                    doc += f"| `{name}` | `{param_type}` | {required} | {param_desc} |\n"
                doc += "\n"
            
            if header_params:
                doc += "#### Header Parameters\n\n"
                doc += "| Name | Type | Required | Description |\n"
                doc += "|------|------|----------|-------------|\n"
                for param in header_params:
                    name = param.get("name", "")
                    param_type = param.get("type", "string")
                    required = "✅ Yes" if param.get("required", False) else "❌ No"
                    param_desc = param.get("description", "No description provided")
                    doc += f"| `{name}` | `{param_type}` | {required} | {param_desc} |\n"
                doc += "\n"
            
            if body_params or form_params:
                doc += "#### Request Body\n\n"
                if body_params:
                    doc += "**Content-Type:** `application/json`\n\n"
                    doc += "| Name | Type | Required | Description |\n"
                    doc += "|------|------|----------|-------------|\n"
                    for param in body_params:
                        name = param.get("name", "")
                        param_type = param.get("type", "string")
                        required = "✅ Yes" if param.get("required", False) else "❌ No"
                        param_desc = param.get("description", "No description provided")
                        doc += f"| `{name}` | `{param_type}` | {required} | {param_desc} |\n"
                    doc += "\n"
                elif form_params:
                    doc += "**Content-Type:** `application/x-www-form-urlencoded`\n\n"
                    doc += "| Name | Type | Required | Description |\n"
                    doc += "|------|------|----------|-------------|\n"
                    for param in form_params:
                        name = param.get("name", "")
                        param_type = param.get("type", "string")
                        required = "✅ Yes" if param.get("required", False) else "❌ No"
                        param_desc = param.get("description", "No description provided")
                        doc += f"| `{name}` | `{param_type}` | {required} | {param_desc} |\n"
                    doc += "\n"
        else:
            doc += "### Parameters\n\n*No parameters required.*\n\n"
        
        # Responses section
        responses = endpoint.get("responses", [])
        if responses:
            doc += "### Responses\n\n"
            for response in responses:
                status = response.get("status", 200)
                resp_desc = response.get("description", "")
                example = response.get("example", {})
                
                # Status code with emoji
                if 200 <= status < 300:
                    status_emoji = "✅"
                elif 400 <= status < 500:
                    status_emoji = "❌"
                elif 500 <= status < 600:
                    status_emoji = "💥"
                else:
                    status_emoji = "ℹ️"
                    
                doc += f"#### {status_emoji} {status} - {resp_desc}\n\n"
                
                if example:
                    doc += "**Example Response:**\n\n"
                    doc += "```json\n"
                    doc += json.dumps(example, indent=2)
                    doc += "\n```\n\n"
        else:
            doc += "### Responses\n\n*No response examples available.*\n\n"
        
        # Add separator between endpoints (but not after the last one)
        if i < len(endpoints):
            doc += "---\n\n"
    
    # Footer
    doc += "\n---\n\n"
    doc += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return doc

def generate_compact_markdown(endpoints: List[Dict]) -> str:
    """Generate compact Markdown documentation"""
    doc = "# API Endpoints\n\n"
    doc += "Quick reference for all available API endpoints.\n\n"
    
    # Group by HTTP method for better organization
    methods_groups = {}
    for endpoint in endpoints:
        method = endpoint.get("method", "GET")
        if method not in methods_groups:
            methods_groups[method] = []
        methods_groups[method].append(endpoint)
    
    # Generate sections by HTTP method
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        if method not in methods_groups:
            continue
            
        doc += f"## {method} Endpoints\n\n"
        
        for endpoint in methods_groups[method]:
            raw_path = endpoint.get("path", "")
            clean_path = extract_clean_path_from_string(raw_path)
            description = endpoint.get("description", "")
            controller = endpoint.get("controller", "")
            action = endpoint.get("action", "")
            
            doc += f"- **{clean_path}**"
            if description:
                doc += f" - {description}"
            if controller and action:
                doc += f" (`{controller}#{action}`)"
            doc += "\n"
        
        doc += "\n"
    
    doc += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return doc

if __name__ == "__main__":
    print("Starting Rails API MCP Server...")
    mcp.run()
