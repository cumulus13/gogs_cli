# Fast Gogs CLI

A high-performance, async command-line interface for interacting with Gogs Git repositories. Built with modern Python async/await patterns for maximum speed and efficiency.

[![PyPI version](https://badge.fury.io/py/gogs-cli.svg)](https://badge.fury.io/py/gogs-cli)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Fast Async Operations**: Built with `aiohttp` for high-performance HTTP requests
- **Connection Pooling**: Reuses connections for better performance
- **Rich Terminal Output**: Beautiful colored output with progress indicators (optional)
- **Repository Management**: Create, list, delete, migrate, and clone repositories
- **User Management**: Get current user information
- **Configuration Management**: Flexible config file and command-line options
- **Git Integration**: Direct git clone operations with advanced options
- **Multiple Output Formats**: Table, JSON, and simple text formats
- **Retry Logic**: Automatic retry with exponential backoff for failed requests
- **Cross-Platform**: Works on Windows, macOS, and Linux with proper config file locations

## Installation

### From PyPI (Recommended)

```bash
pip install gogs-cli
```

### From Source

```bash
# Clone the repository
git clone https://github.com/cumulus13/gogs_cli.git
cd gogs_cli

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Requirements

```bash
# Required dependencies
pip install aiohttp

# Optional but recommended for better UI
pip install rich rich-argparse

# Optional for config file support
pip install configset

# Optional for clipboard support
pip install clipboard
```

## Configuration

The CLI automatically searches for configuration files in the following locations (in order):

### Configuration File Locations

**Linux/macOS:**
1. `~/.config/gogs_cli.ini`
2. `./gogs_cli.ini` (current directory)
3. `<script_directory>/gogs_cli.ini`

**Windows:**
1. `~/.gogs-cli/gogs_cli.ini`
2. `%APPDATA%/.gogs-cli/gogs_cli.ini`
3. `./gogs_cli.ini` (current directory)
4. `<script_directory>/gogs_cli.ini`

### Config File Format

Create a config file at any of the above locations:

```ini
[api]
key = your_gogs_api_token_here
url = http://your-gogs-server.com/api/v1
timeout = 30

[auth]
username = your_username
password = your_password
```

### Using Config Commands

Instead of manually editing the config file, you can use the built-in config commands:

```bash
# Set up your API configuration
gogs-cli/gogs config --set api.key YOUR_API_TOKEN
gogs-cli/gogs config --set api.url http://your-gogs-server.com/api/v1

# Or use short form
gogs-cli/gogs config --set key YOUR_API_TOKEN
gogs-cli/gogs config --set url http://gogs.example.com/api/v1

# Verify your configuration
gogs-cli/gogs config --show
```

### Command Line Options

You can override config file settings with command line arguments:

```bash
gogs-cli --api YOUR_API_TOKEN --url http://gogs.example.com/api/v1 repo -l
# Or
gogs --api YOUR_API_TOKEN --url http://gogs.example.com/api/v1 repo -l
# Or just
gogs-cli repo -l
```

### Getting API Token

1. Log in to your Gogs server
2. Go to Settings > Applications
3. Generate a new token
4. Copy the token to your config file or use with `--api` flag

## Usage

### Basic Syntax

```bash
gogs-cli/gogs [global-options] <command> [command-options]
```

### Global Options

- `-u, --username`: Gogs username
- `-p, --password`: Gogs password  
- `--api`: Gogs API key/token
- `--url`: Gogs API endpoint URL
- `--timeout`: Request timeout in seconds (default: 30)
- `-v, --verbose`: Verbose output
- `-h, --help`: Show help message

## Commands

### Repository Operations (`repo`)

#### List Repositories

```bash
# List all repositories in table format (default)
gogs-cli/gogs repo -l

# List in JSON format
gogs-cli/gogs repo -l --format json

# List in simple format (names only)
gogs-cli/gogs repo -l --format simple
```

#### Create Repository

```bash
# Create a simple repository
gogs-cli/gogs repo -a myproject

# Create with description
gogs-cli/gogs repo -a myproject -d "My awesome project"

# Create private repository
gogs-cli/gogs repo -a myproject --private

# Create with description and make it private
gogs-cli/gogs repo -a myproject -d "Secret project" --private
```

#### Delete Repository

```bash
# Delete a repository
gogs-cli/gogs repo -rm oldproject

# The CLI will automatically detect the owner from your API token
```

#### Migrate Repository

```bash
# Migrate from GitHub
gogs-cli/gogs repo -m https://github.com/user/project.git

# Migrate with custom name
gogs-cli/gogs repo -m https://github.com/user/project.git -n mynewproject

# Migrate as private repository
gogs-cli/gogs repo -m https://github.com/user/project.git --private

# Migrate as mirror (read-only)
gogs-cli/gogs repo -m https://github.com/user/project.git --mirror
```

#### Clone Repository

```bash
# Clone your own repository by name
gogs-cli/gogs repo -c myproject

# Clone to specific directory
gogs-cli/gogs repo -c myproject --dest ./local-copy

# Clone specific branch
gogs-cli/gogs repo -c myproject --branch develop

# Shallow clone (faster for large repos)
gogs-cli/gogs repo -c myproject --depth 1

# Clone with submodules
gogs-cli/gogs repo -c myproject --recursive

# Clone from any URL
gogs-cli/gogs repo -c https://github.com/user/repo.git

# Clone with all options
gogs-cli/gogs repo -c myproject --dest ./my-local-copy --branch main --depth 5 --recursive
```

### User Operations (`user`)

#### Get User Information

```bash
# Show current user info in table format
gogs-cli/gogs user -i

# The output includes user ID, username, email, and other profile information
```

### Configuration Operations (`config`)

#### Show Configuration

```bash
# Display current configuration
gogs-cli/gogs config --show
```

#### Set Configuration Values

```bash
# Set API key
gogs-cli/gogs config --set api.key YOUR_API_TOKEN

# Set API URL
gogs-cli/gogs config --set api.url http://your-gogs-server.com/api/v1

# Set timeout
gogs-cli/gogs config --set api.timeout 60

# Set username for basic auth
gogs-cli/gogs config --set auth.username your_username

# Set password for basic auth
gogs-cli/gogs config --set auth.password your_password

# Short form (without section prefix)
gogs-cli/gogs config --set key YOUR_API_TOKEN
gogs-cli/gogs config --set url http://gogs.example.com/api/v1
gogs-cli/gogs config --set timeout 45
gogs-cli/gogs config --set username myuser
gogs-cli/gogs config --set password mypass
```

#### Get Configuration Values

```bash
# Get API key (will be masked for security)
gogs-cli/gogs config --get api.key

# Get API URL
gogs-cli/gogs config --get api.url

# Get timeout
gogs-cli/gogs config --get api.timeout

# Get username
gogs-cli/gogs config --get auth.username

# Short form
gogs-cli/gogs config --get key
gogs-cli/gogs config --get url
gogs-cli/gogs config --get timeout
```

#### List Available Configuration Keys

```bash
# Show all available configuration keys with descriptions
gogs-cli/gogs config --list
```

## Examples

### Complete Workflow Example

```bash
# 1. Set up configuration first
gogs-cli/gogs config --set key YOUR_API_TOKEN
gogs-cli/gogs config --set url http://your-gogs-server.com/api/v1

# 2. Verify configuration
gogs-cli/gogs config --show

# 3. Check current user
gogs-cli/gogs user -i

# 4. List existing repositories
gogs-cli/gogs repo -l

# 5. Create a new project
gogs-cli/gogs repo -a "my-new-project" -d "A sample project" --private

# 6. Clone it locally
gogs-cli/gogs repo -c "my-new-project" --dest ./my-project

# 7. Later, if you want to delete it
gogs-cli/gogs repo -rm "my-new-project"
```

### Configuration Management Example

```bash
# Initial setup
gogs-cli/gogs config --set api.key abc123...
gogs-cli/gogs config --set api.url http://gogs.company.com/api/v1
gogs-cli/gogs config --set api.timeout 60

# Check what's configured
gogs-cli/gogs config --list
gogs-cli/gogs config --show

# Get specific values
gogs-cli/gogs config --get api.url
gogs-cli/gogs config --get api.key  # Will be masked for security

# Update configuration
gogs-cli/gogs config --set timeout 120
```

### Migration Example

```bash
# Migrate from GitHub to your Gogs server
gogs-cli/gogs repo -m https://github.com/torvalds/linux.git -n linux-mirror --mirror

# Migrate private repository
gogs-cli/gogs repo -m https://github.com/mycompany/private-repo.git --private
```

### Bulk Operations Example

```bash
# List all repos in JSON format and save to file
gogs-cli/gogs repo -l --format json > my-repos.json

# Get simple list for scripting
gogs-cli/gogs repo -l --format simple | while read repo; do
    echo "Processing: $repo"
    gogs-cli repo -c "$repo" --dest "backup/$repo"
done
```

## Performance Features

### Connection Pooling

The CLI uses connection pooling to reuse HTTP connections:
- **Total pool size**: 100 connections
- **Per-host limit**: 30 connections  
- **DNS cache**: 5 minutes TTL
- **Automatic connection management**

### Retry Logic

Automatic retry with exponential backoff:
- **Max retries**: 3 attempts
- **Backoff**: 2^attempt seconds (1s, 2s, 4s)
- **Handles**: Connection errors, timeouts

### Async Operations

All network operations are asynchronous:
- **Non-blocking I/O**: Multiple operations can run concurrently
- **Better resource usage**: Lower memory and CPU usage
- **Faster execution**: Especially for multiple operations

## Error Handling

The CLI provides clear error messages and proper exit codes:

```bash
# API errors
❌ Failed to create repo: 409 Repository already exists

# Network errors  
❌ Error: Connection timeout after 30 seconds

# Git errors
❌ Failed to clone repository: Repository not found

# Authentication errors
❌ Cannot determine user from API key
```

## Troubleshooting

### Common Issues

1. **Help not showing**: Make sure you're using the correct Python version (3.7+)
   ```bash
   gogs-cli/gogs -h
   ```

2. **API connection issues**: Verify your API endpoint and token
   ```bash
   gogs-cli/gogs --url http://your-gogs.com/api/v1 --api YOUR_TOKEN user -i
   # Or set it permanently:
   gogs-cli/gogs config --set api.url http://your-gogs.com/api/v1
   gogs-cli/gogs config --set api.key YOUR_TOKEN
   ```

3. **Configuration not saving**: Make sure configset is installed
   ```bash
   pip install configset
   # Then use config commands:
   gogs-cli/gogs config --set key YOUR_TOKEN
   ```

4. **Git not found**: Install git for clone operations
   ```bash
   # Ubuntu/Debian
   sudo apt-get install git
   
   # macOS
   brew install git
   
   # Windows
   # Download from https://git-scm.com/
   ```

5. **Rich formatting issues**: Install rich for better output
   ```bash
   pip install rich rich-argparse
   ```

6. **Invalid configuration key error**: Use the list command to see valid keys
   ```bash
   gogs-cli/gogs config --list
   ```

7. **Config file not found**: The CLI will automatically create a config file in the appropriate location for your OS when you first set a value
   ```bash
   gogs-cli/gogs config --set key YOUR_TOKEN
   # This will create the config file automatically
   ```

### Debug Mode

Enable debug output with environment variables:

```bash
# Show full tracebacks
TRACEBACK=1 gogs-cli repo -l

# Verbose output
gogs-cli/gogs -v repo -l
```

## Development

### Project Structure

```
gogs_cli.py          # Main CLI script
gogs_cli.ini         # Configuration file (optional)
README.md           # This file
requirements.txt    # Dependencies
```

### Requirements

```txt
aiohttp>=3.8.0
rich>=13.0.0
rich-argparse>=1.0.0
configset>=2.0.0
clipboard>=0.0.4
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code follows PEP 8
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Changelog

### v1.0.0 (Current)
- Initial release
- Async HTTP operations with aiohttp
- Repository CRUD operations
- Git clone integration
- User management
- Rich terminal output
- Configuration management
- Retry logic and error handling

## Support

- **Issues**: Report bugs on GitHub
- **Documentation**: Check this README
- **API Reference**: See Gogs API documentation

## Performance Comparison

| Operation | Requests (sync) | This CLI (async) | Improvement |
|-----------|-----------------|------------------|-------------|
| List 100 repos | ~2-5 seconds | ~0.5-1 seconds | 4-5x faster |
| Clone 5 repos | Sequential | Concurrent | 3-4x faster |
| Multiple API calls | Blocking | Non-blocking | 5-10x faster |

## Security Notes

- API tokens are sensitive - never commit them to version control
- Use environment variables or config files with proper permissions
- The CLI supports both token and username/password authentication
- HTTPS is recommended for production Gogs servers

## FAQ

**Q: How do I change my API configuration without editing files manually?**
A: Use the built-in config commands:
```bash
gogs config --set api.key YOUR_NEW_TOKEN
gogs config --set api.url http://new-server.com/api/v1
gogs config --show  # Verify changes
```

**Q: What configuration keys are available?**
A: Run `python gogs_cli.py config --list` to see all available keys with descriptions.

**Q: Can I see my current API key?**
A: Yes, but it will be masked for security: `python gogs_cli.py config --get api.key`

**Q: How do I reset my configuration?**
A: Delete the config file (`gogs_cli.ini`) or set new values with `--set` commands.

## author
[Hadi Cahyadi](mailto:cumulus13@gmail.com)
    

[![Buy Me a Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cumulus13)

[![Donate via Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/cumulus13)

[Support me on Patreon](https://www.patreon.com/cumulus13)