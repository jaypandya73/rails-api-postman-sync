# Rails API MCP Server

🚀 **Automatically analyze Rails controllers and sync API documentation to Postman collections using Claude and MCP.**

A standalone Python MCP server that intelligently analyzes your Rails controllers and keeps your Postman collections perfectly synchronized with your codebase. No package installation required - just download, configure, and run!

## ✨ Features

- **🔍 Smart Controller Analysis**: Automatically extracts API endpoints from Rails controller code
- **🛣️ Route Integration**: Reads your Rails `routes.rb` for accurate endpoint paths and HTTP methods
- **📋 Postman Sync**: Updates Postman collections with intelligent merging and conflict resolution
- **📚 Documentation Generation**: Creates comprehensive API docs in Markdown or JSON formats
- **👀 Preview Changes**: See exactly what will be updated before applying changes
- **🛡️ Smart Preservation**: Protects existing manual documentation while adding auto-generated content
- **🔄 Intelligent Merging**: Detects and preserves manual content while updating auto-generated sections
- **⚙️ Fully Customizable**: Single Python file - modify and extend as needed

## 🎯 Perfect For

- **Rails Developers** maintaining Postman collections for API testing
- **Development Teams** wanting automated API documentation workflows  
- **DevOps Engineers** setting up documentation pipelines
- **API Maintainers** tired of manually syncing Rails APIs with Postman
- **Teams** who need customized documentation workflows

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ with pip
- Claude (Anthropic) with MCP support
- Postman account with API access
- Rails application

### 1. Download & Setup

**Option A: Clone Repository (Recommended)**
```bash
git clone https://github.com/jaypandya73/rails-api-postman-sync
cd rails-api-mcp-server
```

**Option B: Download Single File**
```bash
# Download just the main server file
wget https://raw.githubusercontent.com/jaypandya73/rails-api-postman-sync/main/rails_api_postman_sync.py
```

### 2. Install Dependencies

```bash
pip install mcp requests fastmcp
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### 3. Configure Claude MCP

Add to your Claude MCP configuration file:

```json
{
  "mcpServers": {
    "rails-api-server": {
      "command": "python",
      "args": ["/path/to/rails_api_mcp_server.py"],
      "env": {
        "RAILS_PROJECT_PATH": "/path/to/your/rails/app",
        "POSTMAN_COLLECTION_UID": "your-postman-collection-uid", 
        "POSTMAN_API_KEY": "your-postman-api-key"
      }
    }
  }
}
```

### 4. Get Your Postman Credentials

**Collection UID**: 
1. Open your Postman collection
2. Click "Share" → "Get public link"
3. Copy the UID from the URL: `https://www.postman.com/collections/{THIS_IS_YOUR_UID}`

**API Key**:
1. Go to [Postman API Keys](https://web.postman.co/settings/me/api-keys)
2. Generate a new API key
3. Copy the key (starts with `PMAK-`)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `RAILS_PROJECT_PATH` | Path to your Rails application root | ✅ Yes | `/Users/john/projects/my-rails-app` |
| `POSTMAN_COLLECTION_UID` | Your Postman collection UID | ✅ Yes | `12345678-1234-1234-1234-123456789abc` |
| `POSTMAN_API_KEY` | Your Postman API key | ✅ Yes | `PMAK-1234567890abcdef` |

### Sample Configuration Files

**macOS/Linux Example**:
```json
{
  "mcpServers": {
    "rails-api-server": {
      "command": "python",
      "args": ["/Users/john/tools/rails_api_mcp_server.py"],
      "env": {
        "RAILS_PROJECT_PATH": "/Users/john/projects/my-rails-app",
        "POSTMAN_COLLECTION_UID": "COLLECTION ID",
        "POSTMAN_API_KEY": "POSTMAN API KEY"
      }
    }
  }
}
```

**Windows Example**:
```json
{
  "mcpServers": {
    "rails-api-server": {
      "command": "python",
      "args": ["C:\\tools\\rails_api_mcp_server.py"],
      "env": {
        "RAILS_PROJECT_PATH": "C:\\projects\\my-rails-app",
        "POSTMAN_COLLECTION_UID": "COLLECTION ID", 
        "POSTMAN_API_KEY": "POSTMAN API KEY"
      }
    }
  }
}
```

## 📖 Usage

### 1. Verify Setup
```
Ask Claude: "Check if the Rails API MCP server is properly configured"
```

### 2. Analyze Controller
```
Ask Claude: "Analyze this Rails controller and index(your action name) action and help me to update it to postman documentation.:

[Paste your controller code here]
```

### 3. Preview Changes (Recommended)
```
Ask Claude: "Preview what changes will be made to my Postman collection before updating"
```

### 4. Update Postman Collection
```
Ask Claude: "Update my Postman collection with the analyzed endpoints"
```

### 5. Generate Documentation
```
Ask Claude: "Generate detailed API documentation in Markdown format"
```
If you take a look at server file then method itself is self explainatory.

## 🛠️ Available Tools

| Tool Name | Description | Use Case |
|-----------|-------------|----------|
| `analyze_rails_controller` | Extract endpoints from controller code | Initial analysis |
| `preview_postman_changes` | Preview changes before applying | Safety check |
| `smart_update_postman_collection` | Update Postman with intelligent merging | Main sync operation |
| `generate_api_documentation` | Create Markdown/JSON docs | Documentation export |
| `check_postman_connection` | Verify credentials and connection | Debugging |

## 🗂️ Available Resources

| Resource | Description | Access |
|----------|-------------|---------|
| `rails://routes` | Your Rails routes.rb file content | Auto-accessed during analysis |

## 📝 Example Workflow

### Step 1: Controller Analysis
Paste your Rails controller:
```ruby
class Api::V1::UsersController < ApplicationController
  before_action :authenticate_user!
  
  # GET /api/v1/users
  def index
    @users = User.page(params[:page]).per(params[:per_page] || 20)
    render json: @users, meta: pagination_meta(@users)
  end
  
  # GET /api/v1/users/:id  
  def show
    @user = User.find(params[:id])
    render json: @user
  rescue ActiveRecord::RecordNotFound
    render json: { error: 'User not found' }, status: :not_found
  end
  
  # POST /api/v1/users
  def create
    @user = User.new(user_params)
    
    if @user.save
      render json: @user, status: :created
    else
      render json: { errors: @user.errors }, status: :unprocessable_entity
    end
  end
  
  private
  
  def user_params
    params.require(:user).permit(:name, :email, :role)
  end
end
```

### Step 2: Automatic Analysis Results
The MCP server will:
- ✅ Read your `routes.rb` for exact paths: `/api/v1/users`, `/api/v1/users/:id`
- ✅ Detect HTTP methods: `GET`, `POST`
- ✅ Extract parameters: `page`, `per_page`, `id`, `user[name]`, etc.
- ✅ Identify response formats and status codes
- ✅ Generate comprehensive documentation

### Step 3: Smart Postman Updates
- 🔄 Updates existing endpoints or creates new ones
- 🛡️ Preserves your existing examples and manual documentation
- 📚 Adds auto-generated comprehensive documentation
- 🏷️ Uses markers to track auto-generated vs manual content

## 🎨 Customization

Since this is a standalone Python file, you can easily customize it:

### Common Customizations

**1. Add Custom Parameter Detection**
```python
# Around line 50, modify analyze_rails_controller function
def analyze_rails_controller(controller_code: str) -> str:
    # Add your custom logic here
    # Example: detect custom authentication headers
    if 'authenticate_user!' in controller_code:
        # Add Authorization header to all endpoints
        pass
```

**2. Custom Documentation Templates**
```python
# Around line 800, modify generate_request_documentation function  
def generate_request_documentation(endpoint: Dict) -> str:
    # Customize the documentation format
    # Add your company-specific templates
    pass
```

**3. Different Response Format Detection**
```python
# Add support for your specific Rails patterns
# Example: JSONAPI, GraphQL endpoints, etc.
```

**4. Integration with Other Tools**
```python
# Add functions to export to Swagger, OpenAPI, etc.
# Integrate with Slack, Teams notifications
# Add custom validation rules
```

## 🔍 Advanced Features

### Smart Documentation Preservation
- **Auto-generated sections** are updated with new information
- **Manual content** is preserved using HTML comment markers
- **Merge conflicts** are handled gracefully with fallback strategies
- **Version tracking** in documentation timestamps

### Intelligent Endpoint Matching
- Handles Rails format extensions (`.json`, `.xml`, `.html`)
- Matches by HTTP method + clean path (ignoring query params)
- Preserves existing request examples and custom headers
- Updates only changed fields, leaves rest untouched

### Flexible Output Formats
- **Detailed Markdown** with tables, examples, and emoji
- **Compact Markdown** for quick reference guides
- **JSON export** for programmatic processing
- **Postman-native** documentation with proper formatting

## 🐛 Troubleshooting

### Common Issues

**❌ "RAILS_PROJECT_PATH not set"**
```bash
# Make sure the path is absolute and points to Rails root
# Should contain: app/, config/, Gemfile
export RAILS_PROJECT_PATH="/full/path/to/rails/app"
```

**❌ "routes.rb not found"**
```bash
# Verify the structure:
ls $RAILS_PROJECT_PATH/config/routes.rb
```

**❌ "Invalid Postman API key"**
- Verify your API key starts with `PMAK-`
- Check it's not expired in Postman settings
- Ensure it has collection read/write permissions

**❌ "Collection not found"**
- Double-check the Collection UID
- Make sure the collection exists in your Postman account
- Verify you have edit permissions

### Debug Mode

Add debug logging by modifying the server file:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

We welcome contributions! This being a standalone file makes it easy to:

1. **Fork** the repository
2. **Modify** `rails_api_mcp_server.py` 
3. **Test** your changes
4. **Submit** a pull request

### Development Tips
- Keep everything in the single file for simplicity
- Add comprehensive docstrings for new functions
- Test with different Rails application structures
- Consider backward compatibility

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[FastMCP](https://github.com/jlowin/fastmcp)** - Excellent MCP server framework
- **[Postman API Format](https://learning.postman.com/collection-format/getting-started/structure-of-a-collection/)** - Comprehensive API for collection management
- **[Claude & MCP](https://modelcontextprotocol.io/)** - Making AI tool integration seamless
- **Rails Community** - For creating such a well-structured framework to analyze

## 📞 Support & Community

- **🐛 Issues**: [GitHub Issues](https://github.com/jaypandya73/rails-api-postman-sync/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/jaypandya73/rails-api-postman-sync/discussions)  
- **📧 Email**: jayved128@gmail.com

## 🌟 Show Your Support

If this tool saved you time and effort, please:
- ⭐ **Star this repository**
- 🐛 **Report issues** you encounter
- 💡 **Suggest features** you'd like to see
- 🤝 **Share** with other Rails developers
- 📝 **Write** about your experience

---

**Made with ❤️ for the Rails community**

*Spend less time on documentation, more time building amazing APIs!*
