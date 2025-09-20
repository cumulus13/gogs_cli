#!/usr/bin/env python3

import asyncio
import aiohttp
import argparse
import json
import sys
import os
import subprocess
import shutil
from pathlib import Path
from typing import ClassVar, Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich_argparse import RichHelpFormatter, _lazy_rich as rr
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Rich not available. Install with: pip install rich rich-argparse")

try:
    from configset import configset
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

try:
    import clipboard
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

@dataclass
class GogsConfig:
    """Configuration management for Gogs CLI"""
    api_key: str = "c895e3636e813df4dbe9d01aed4bff0e14fc99b5"
    api_url: str = "http://gogs.container.com/api/v1"
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3

class CustomRichHelpFormatter(RichHelpFormatter if RICH_AVAILABLE else argparse.HelpFormatter):
    """A custom RichHelpFormatter with modified styles."""
    if RICH_AVAILABLE:
        styles: ClassVar[dict[str, rr.StyleType]] = {
            "argparse.args": "bold #FFFF00",
            "argparse.groups": "#AA55FF", 
            "argparse.help": "bold #00FFFF",
            "argparse.metavar": "bold #FF00FF",
            "argparse.syntax": "underline",
            "argparse.text": "white",
            "argparse.prog": "bold #00AAFF italic",
            "argparse.default": "bold",
        }

class GogsAPI:
    """Async Gogs API client with connection pooling and retry logic"""
    
    def __init__(self, config: GogsConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._user_cache: Optional[Dict[str, Any]] = None
    
    @asynccontextmanager
    async def get_session(self):
        """Context manager for aiohttp session with connection pooling"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Per host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self._get_headers()
            )
        
        try:
            yield self.session
        finally:
            pass  # Keep session alive for reuse
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if self.config.api_key:
            return {'Authorization': f'token {self.config.api_key}'}
        return {}
    
    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """Get basic auth if no API key"""
        if not self.config.api_key and self.config.username and self.config.password:
            return aiohttp.BasicAuth(self.config.username, self.config.password)
        return None
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with retry logic"""
        url = f"{self.config.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.get_session() as session:
                    auth = self._get_auth()
                    async with session.request(method, url, auth=auth, **kwargs) as response:
                        # Create a new response object with content loaded
                        content = await response.read()
                        # Create a mock response object to return
                        response._content = content
                        return response
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user info with caching"""
        if self._user_cache:
            return self._user_cache
        
        try:
            response = await self._make_request('GET', '/user')
            if response.status == 200:
                user_data = json.loads(response._content.decode())
                self._user_cache = user_data
                return user_data
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error getting user info:[/] {e}")
        return None
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List user repositories"""
        try:
            response = await self._make_request('GET', '/user/repos')
            if response.status == 200:
                return json.loads(response._content.decode())
            else:
                if console:
                    console.print(f"❌ [red]Failed to list repos: {response.status}[/]")
                return []
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error listing repos:[/] {e}")
            return []
    
    async def create_repository(self, name: str, description: str = "", private: bool = False) -> bool:
        """Create a new repository"""
        data = {
            "name": name,
            "description": description,
            "private": private
        }
        
        try:
            response = await self._make_request('POST', '/user/repos', json=data)
            if response.status == 201:
                if console:
                    console.print(f"✅ [green]Repository '{name}' created successfully.[/]")
                return True
            else:
                error_text = response._content.decode()
                if console:
                    console.print(f"❌ [red]Failed to create repo: {response.status} {error_text}[/]")
                return False
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error creating repository:[/] {e}")
            return False
    
    async def delete_repository(self, name: str) -> bool:
        """Delete a repository"""
        user = await self.get_current_user()
        if not user:
            if console:
                console.print("❌ [red]Cannot determine owner from API key.[/]")
            return False
        
        owner = user.get("login") or user.get("username")
        
        try:
            response = await self._make_request('DELETE', f'/repos/{owner}/{name}')
            if response.status == 204:
                if console:
                    console.print(f"🗑️ [green]Repository '{name}' deleted successfully.[/]")
                return True
            elif response.status == 404:
                if console:
                    console.print(f"⚠️ [yellow]Repository '{name}' not found.[/]")
                return False
            else:
                error_text = response._content.decode()
                if console:
                    console.print(f"❌ [red]Failed to delete repo: {response.status} {error_text}[/]")
                return False
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error deleting repository:[/] {e}")
            return False
    
    async def migrate_repository(self, clone_url: str, repo_name: str, 
                               private: bool = False, mirror: bool = False) -> bool:
        """Migrate/clone repository from another server"""
        user = await self.get_current_user()
        if not user:
            if console:
                console.print("❌ [red]Cannot determine user ID from API key.[/]")
            return False
        
        data = {
            "clone_addr": clone_url,
            "uid": user.get("id"),
            "repo_name": repo_name,
            "mirror": mirror,
            "private": private
        }
        
        try:
            if console:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                    task = progress.add_task(f"Migrating repository '{repo_name}'...", total=None)
                    response = await self._make_request('POST', '/repos/migrate', json=data)
            else:
                response = await self._make_request('POST', '/repos/migrate', json=data)
            
            if response.status in (200, 201):
                if console:
                    console.print(f"📦 [green]Repository '{repo_name}' migrated successfully from {clone_url}[/]")
                return True
            else:
                error_text = response._content.decode()
                if console:
                    console.print(f"❌ [red]Failed to migrate repo: {response.status} {error_text}[/]")
                return False
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error migrating repository:[/] {e}")
            return False
    
    async def get_repository_info(self, owner: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information"""
        try:
            response = await self._make_request('GET', f'/repos/{owner}/{repo_name}')
            if response.status == 200:
                return json.loads(response._content.decode())
            return None
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error getting repository info:[/] {e}")
            return None

class GitOperations:
    """Git operations for cloning repositories"""
    
    @staticmethod
    def check_git_available() -> bool:
        """Check if git is available in the system"""
        return shutil.which("git") is not None
    
    @staticmethod
    async def clone_repository(clone_url: str, destination: Optional[str] = None, 
                             branch: Optional[str] = None, depth: Optional[int] = None,
                             recursive: bool = False) -> bool:
        """Clone a repository using git"""
        if not GitOperations.check_git_available():
            if console:
                console.print("❌ [red]Git is not available. Please install git first.[/]")
            else:
                print("Git is not available. Please install git first.")
            return False
        
        cmd = ["git", "clone"]
        
        if depth:
            cmd.extend(["--depth", str(depth)])
        
        if branch:
            cmd.extend(["--branch", branch])
        
        if recursive:
            cmd.append("--recursive")
        
        cmd.append(clone_url)
        
        if destination:
            cmd.append(destination)
        
        try:
            if console:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                    task = progress.add_task(f"Cloning repository...", total=None)
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                repo_name = destination or clone_url.split('/')[-1].replace('.git', '')
                if console:
                    console.print(f"✅ [green]Repository cloned successfully to '{repo_name}'[/]")
                else:
                    print(f"Repository cloned successfully to '{repo_name}'")
                return True
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                if console:
                    console.print(f"❌ [red]Failed to clone repository:[/] {error_msg}")
                else:
                    print(f"Failed to clone repository: {error_msg}")
                return False
                
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error cloning repository:[/] {e}")
            else:
                print(f"Error cloning repository: {e}")
            return False

class CLI:
    """Enhanced command-line interface for interacting with Gogs API."""
    
    def __init__(self):
        
        self.config_file = ''

        self.config_file_list = [
            Path(os.path.expanduser('~')) / '.gogs-cli' / f"{Path(__file__).stem}.ini" if sys.platform == 'win32' else Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.ini",
            Path(os.path.expandvars('%APPDATA%')) / '.gogs-cli' / f"{Path(__file__).stem}.ini" if sys.platform == 'win32' else Path(os.path.expanduser('~')) / '.config' / f"{Path(__file__).stem}.ini",
            Path.cwd() / f"{Path(__file__).stem}.ini",
            Path(__file__).parent / f"{Path(__file__).stem}.ini"
        ]
        for cf in self.config_file_list:
            if cf.is_file():
                self.config_file = cf
                break

        self.config_file = self.config_file or Path(__file__).parent / f"{Path(__file__).stem}.ini"
        self.config = self._load_config()
        self.api = GogsAPI(self.config)
    
    def _load_config(self) -> GogsConfig:
        """Load configuration from file or use defaults"""
        config = GogsConfig()
        
        if CONFIG_AVAILABLE and self.config_file.exists():
            try:
                file_config = configset(str(self.config_file))
                config.api_key = file_config.get_config('api', 'key', config.api_key)
                config.api_url = file_config.get_config('api', 'url', config.api_url)
                config.username = file_config.get_config('auth', 'username', config.username)
                config.password = file_config.get_config('auth', 'password', config.password)
                config.timeout = int(file_config.get_config('api', 'timeout', str(config.timeout)))
            except Exception:
                pass  # Use defaults
        
        return config
    
    def _get_config_handler(self):
        """Get config handler, create file if needed"""
        if not CONFIG_AVAILABLE:
            if console:
                console.print("❌ [red]configset package not available. Install with: pip install configset[/]")
            else:
                print("configset package not available. Install with: pip install configset")
            return None
        
        # Create config file if it doesn't exist
        if not self.config_file.exists():
            self.config_file.touch()
        
        return configset(str(self.config_file))
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create and configure argument parser"""
        formatter_class = CustomRichHelpFormatter if RICH_AVAILABLE else argparse.HelpFormatter
        
        parser = argparse.ArgumentParser(
            description="Fast Gogs CLI - Interact with Gogs API using async HTTP",
            formatter_class=formatter_class
        )
        
        # Global options
        parser.add_argument('-u', '--username', help='Gogs username')
        parser.add_argument('-p', '--password', help='Gogs password')
        parser.add_argument('--api', help='Gogs API key', default=self.config.api_key)
        parser.add_argument('--url', help='Gogs API endpoint', default=self.config.api_url)
        parser.add_argument('--timeout', type=int, help='Request timeout in seconds', default=self.config.timeout)
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Repository commands
        repo_parser = subparsers.add_parser('repo', help='Repository operations', formatter_class=formatter_class)
        repo_parser.add_argument('-l', '--list', action='store_true', help='List repositories')
        repo_parser.add_argument('-a', '--add', metavar='REPO_NAME', help='Create new repository')
        repo_parser.add_argument('-rm', '--remove', metavar='REPO_NAME', help='Remove repository')
        repo_parser.add_argument('-m', '--migrate', metavar='CLONE_URL', help='Migrate/clone repository from URL')
        repo_parser.add_argument('-c', '--clone', metavar='REPO_NAME_OR_URL', help='Clone repository locally')
        
        # Additional options for repo commands
        repo_parser.add_argument('-n', '--name', metavar='REPO_NAME', 
                               help='Repository name for migration (defaults to last part of URL)')
        repo_parser.add_argument('-d', '--description', metavar='DESCRIPTION', 
                               help='Repository description', default="")
        repo_parser.add_argument('--private', action='store_true', help='Create private repository')
        repo_parser.add_argument('--mirror', action='store_true', help='Create as mirror repository')
        repo_parser.add_argument('--format', choices=['table', 'json', 'simple'], 
                               default='table', help='Output format for list command')
        
        # Clone-specific options
        repo_parser.add_argument('--dest', metavar='DIRECTORY', help='Destination directory for clone')
        repo_parser.add_argument('--branch', metavar='BRANCH', help='Branch to clone')
        repo_parser.add_argument('--depth', type=int, metavar='N', help='Shallow clone with depth N')
        repo_parser.add_argument('--recursive', action='store_true', help='Clone submodules recursively')
        
        # User commands
        user_parser = subparsers.add_parser('user', help='User operations', formatter_class=formatter_class)
        user_parser.add_argument('-i', '--info', action='store_true', help='Show current user info')
        
        # Config commands
        config_parser = subparsers.add_parser('config', help='Configuration operations', formatter_class=formatter_class)
        config_group = config_parser.add_mutually_exclusive_group()
        config_group.add_argument('--show', action='store_true', help='Show current configuration')
        config_group.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set configuration value (e.g., --set api.key YOUR_TOKEN)')
        config_group.add_argument('--get', metavar='KEY', help='Get configuration value (e.g., --get api.key)')
        config_group.add_argument('--list', action='store_true', help='List all configuration keys')
        
        return parser
    
    async def handle_repo_command(self, args):
        """Handle repository-related commands"""
        # Check which action is specified
        actions_specified = sum([
            bool(args.list),
            bool(args.add), 
            bool(args.remove),
            bool(args.migrate),
            bool(args.clone)
        ])
        
        if actions_specified == 0:
            if console:
                console.print("⚠️ [yellow]No repo action specified. Use 'python script.py repo -h' for help.[/]")
            else:
                print("No repo action specified. Use 'python script.py repo -h' for help.")
            return
        
        if actions_specified > 1:
            if console:
                console.print("⚠️ [yellow]Please specify only one action at a time.[/]")
            else:
                print("Please specify only one action at a time.")
            return
        
        if args.list:
            await self.list_repositories(args)
        elif args.add:
            await self.create_repository(args)
        elif args.remove:
            await self.delete_repository(args)
        elif args.migrate:
            await self.migrate_repository(args)
        elif args.clone:
            await self.clone_repository(args)
    
    async def list_repositories(self, args):
        """List repositories with different output formats"""
        repos = await self.api.list_repositories()
        
        if not repos:
            if console:
                console.print("⚠️ [yellow]No repositories found.[/]")
            else:
                print("No repositories found.")
            return
        
        if args.format == 'json':
            print(json.dumps(repos, indent=2))
        elif args.format == 'simple':
            for repo in repos:
                print(repo['name'])
        else:  # table format
            if console:
                table = Table(title="📋 Repositories")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Description", style="white")
                table.add_column("Private", style="yellow")
                table.add_column("Clone URL", style="green")
                
                for repo in repos:
                    table.add_row(
                        repo['name'],
                        repo.get('description', ''),
                        "Yes" if repo.get('private', False) else "No",
                        repo.get('clone_url', '')
                    )
                console.print(table)
            else:
                print("Name\tDescription\tPrivate\tClone URL")
                for repo in repos:
                    print(f"{repo['name']}\t{repo.get('description', '')}\t"
                          f"{'Yes' if repo.get('private', False) else 'No'}\t"
                          f"{repo.get('clone_url', '')}")
    
    async def create_repository(self, args):
        """Create a new repository"""
        await self.api.create_repository(args.add, args.description, args.private)
    
    async def delete_repository(self, args):
        """Delete a repository"""
        await self.api.delete_repository(args.remove)
    
    async def migrate_repository(self, args):
        """Migrate a repository"""
        repo_name = args.name or args.migrate.split('/')[-1].replace('.git', '')
        await self.api.migrate_repository(args.migrate, repo_name, args.private, args.mirror)
    
    async def clone_repository(self, args):
        """Clone a repository locally"""
        clone_target = args.clone
        
        # Check if it's a repository name or full URL
        if not (clone_target.startswith('http://') or clone_target.startswith('https://') or clone_target.startswith('git@')):
            # It's a repository name, we need to get the clone URL from the API
            user = await self.api.get_current_user()
            if not user:
                if console:
                    console.print("❌ [red]Cannot determine user from API key.[/]")
                else:
                    print("Cannot determine user from API key.")
                return
            
            owner = user.get("login") or user.get("username")
            repo_info = await self.api.get_repository_info(owner, clone_target)
            
            if not repo_info:
                if console:
                    console.print(f"❌ [red]Repository '{clone_target}' not found.[/]")
                else:
                    print(f"Repository '{clone_target}' not found.")
                return
            
            clone_url = repo_info.get('clone_url') or repo_info.get('ssh_url')
            if not clone_url:
                if console:
                    console.print(f"❌ [red]No clone URL found for repository '{clone_target}'.[/]")
                else:
                    print(f"No clone URL found for repository '{clone_target}'.")
                return
        else:
            clone_url = clone_target
        
        # Perform the git clone
        await GitOperations.clone_repository(
            clone_url, 
            args.dest, 
            args.branch, 
            args.depth,
            args.recursive
        )
    
    async def handle_user_command(self, args):
        """Handle user-related commands"""
        if args.info:
            user = await self.api.get_current_user()
            if user:
                if console:
                    table = Table(title="👤 User Information")
                    table.add_column("Field", style="cyan")
                    table.add_column("Value", style="white")
                    
                    for key, value in user.items():
                        table.add_row(str(key), str(value))
                    console.print(table)
                else:
                    print(json.dumps(user, indent=2))
            else:
                if console:
                    console.print("❌ [red]Failed to get user information.[/]")
                else:
                    print("Failed to get user information.")
    
    def handle_config_command(self, args):
        """Handle configuration commands"""
        if args.show:
            self._show_config()
        elif args.set:
            self._set_config(args.set[0], args.set[1])
        elif args.get:
            self._get_config(args.get)
        elif args.list:
            self._list_config_keys()
        else:
            if console:
                console.print("⚠️ [yellow]No config action specified. Use 'python script.py config -h' for help.[/]")
            else:
                print("No config action specified. Use 'python script.py config -h' for help.")
    
    def _show_config(self):
        """Show current configuration"""
        config_dict = {
            'api_url': self.config.api_url,
            'api_key': f"{self.config.api_key[:8]}..." if self.config.api_key else None,
            'username': self.config.username,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries
        }
        
        if console:
            table = Table(title="⚙️ Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in config_dict.items():
                table.add_row(key, str(value) if value is not None else "Not set")
            console.print(table)
        else:
            print(json.dumps(config_dict, indent=2))
    
    def _set_config(self, key: str, value: str):
        """Set configuration value"""
        config_handler = self._get_config_handler()
        if not config_handler:
            return
        
        # Parse the key (e.g., "api.key" -> section="api", option="key")
        if '.' in key:
            section, option = key.split('.', 1)
        else:
            # Default section based on key
            if key in ['key', 'url', 'timeout']:
                section = 'api'
            elif key in ['username', 'password']:
                section = 'auth'
            else:
                section = 'general'
            option = key
        
        # Validate key
        valid_keys = {
            'api.key', 'api.url', 'api.timeout',
            'auth.username', 'auth.password',
            'key', 'url', 'timeout', 'username', 'password'
        }
        
        full_key = f"{section}.{option}"
        if full_key not in valid_keys and key not in valid_keys:
            if console:
                console.print(f"❌ [red]Invalid configuration key: {key}[/]")
                console.print("Valid keys: api.key, api.url, api.timeout, auth.username, auth.password")
            else:
                print(f"Invalid configuration key: {key}")
                print("Valid keys: api.key, api.url, api.timeout, auth.username, auth.password")
            return
        
        try:
            # Set the configuration
            config_handler.set_config(section, option, value)
            
            # Update current config
            if full_key == 'api.key' or key == 'key':
                self.config.api_key = value
            elif full_key == 'api.url' or key == 'url':
                self.config.api_url = value
            elif full_key == 'api.timeout' or key == 'timeout':
                self.config.timeout = int(value)
            elif full_key == 'auth.username' or key == 'username':
                self.config.username = value
            elif full_key == 'auth.password' or key == 'password':
                self.config.password = value
            
            # Update API instance
            self.api.config = self.config
            
            if console:
                console.print(f"✅ [green]Configuration saved: {key} = {value}[/]")
            else:
                print(f"Configuration saved: {key} = {value}")
                
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error saving configuration:[/] {e}")
            else:
                print(f"Error saving configuration: {e}")
    
    def _get_config(self, key: str):
        """Get configuration value"""
        config_handler = self._get_config_handler()
        if not config_handler:
            return
        
        # Parse the key
        if '.' in key:
            section, option = key.split('.', 1)
        else:
            # Default section based on key
            if key in ['key', 'url', 'timeout']:
                section = 'api'
            elif key in ['username', 'password']:
                section = 'auth'
            else:
                section = 'general'
            option = key
        
        try:
            value = config_handler.get_config(section, option, None)
            if value is not None:
                # Mask sensitive values
                if 'key' in option.lower() or 'password' in option.lower():
                    if len(value) > 8:
                        display_value = f"{value[:8]}..."
                    else:
                        display_value = "***"
                    if console:
                        console.print(f"🔑 [cyan]{key}[/] = [yellow]{display_value}[/] (masked)")
                    else:
                        print(f"{key} = {display_value} (masked)")
                else:
                    if console:
                        console.print(f"📄 [cyan]{key}[/] = [green]{value}[/]")
                    else:
                        print(f"{key} = {value}")
            else:
                if console:
                    console.print(f"⚠️ [yellow]Configuration key '{key}' not found or not set[/]")
                else:
                    print(f"Configuration key '{key}' not found or not set")
                    
        except Exception as e:
            if console:
                console.print(f"❌ [red]Error reading configuration:[/] {e}")
            else:
                print(f"Error reading configuration: {e}")
    
    def _list_config_keys(self):
        """List all available configuration keys"""
        keys_info = [
            ("api.key", "Gogs API token/key"),
            ("api.url", "Gogs API endpoint URL"),
            ("api.timeout", "Request timeout in seconds"),
            ("auth.username", "Gogs username (for basic auth)"),
            ("auth.password", "Gogs password (for basic auth)"),
        ]
        
        if console:
            table = Table(title="📋 Available Configuration Keys")
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            
            for key, description in keys_info:
                table.add_row(key, description)
            console.print(table)
        else:
            print("Available Configuration Keys:")
            for key, description in keys_info:
                print(f"  {key:<15} - {description}")
    
    def update_config_from_args(self, args):
        """Update configuration from command line arguments"""
        if hasattr(args, 'username') and args.username:
            self.config.username = args.username
        if hasattr(args, 'password') and args.password:
            self.config.password = args.password
        if hasattr(args, 'api') and args.api:
            self.config.api_key = args.api
        if hasattr(args, 'url') and args.url:
            self.config.api_url = args.url
        if hasattr(args, 'timeout') and args.timeout:
            self.config.timeout = args.timeout
        
        # Update API instance with new config
        self.api.config = self.config
    
    def run_sync(self):
        """Synchronous main entry point that handles argument parsing"""
        parser = self.create_parser()
        
        # Show help if no arguments provided
        if len(sys.argv) == 1:
            parser.print_help()
            return
        
        try:
            args = parser.parse_args()
            self.update_config_from_args(args)
            
            # Show help if no command provided
            if not hasattr(args, 'command') or not args.command:
                parser.print_help()
                return
            
            # Run the async part
            asyncio.run(self.run_async(args))
                
        except KeyboardInterrupt:
            if console:
                console.print("\n⚠️ [yellow]Operation cancelled by user.[/]")
            else:
                print("\nOperation cancelled by user.")
            sys.exit(1)
        except SystemExit:
            # This happens when argparse encounters -h or invalid args
            raise
        except Exception as e:
            if console:
                console.print(f"❌ [red]Unexpected error:[/] {e}")
            else:
                print(f"Unexpected error: {e}")
            
            if os.getenv('TRACEBACK', '').lower() in ['1', 'true']:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    async def run_async(self, args):
        """Async part of the main function"""
        try:
            if args.command == 'repo':
                await self.handle_repo_command(args)
            elif args.command == 'user':
                await self.handle_user_command(args)
            elif args.command == 'config':
                self.handle_config_command(args)
            else:
                if console:
                    console.print("❌ [red]Unknown command.[/]")
                else:
                    print("Unknown command.")
                sys.exit(1)
        finally:
            await self.api.close()

def main():
    """Main entry point"""
    cli = CLI()
    cli.run_sync()

if __name__ == "__main__":
    main()