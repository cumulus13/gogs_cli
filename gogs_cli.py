#!/usr/bin/env python

import requests
import argparse
from pathlib import Path
from rich.console import Console
from rich_argparse import RichHelpFormatter, _lazy_rich as rr
from typing import ClassVar
import sys
from configset import configset
from pathlib import Path
# import traceback
import os
import clipboard


console = Console()

class CustomRichHelpFormatter(RichHelpFormatter):
    """A custom RichHelpFormatter with modified styles."""

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

class CLI:
    """A command-line interface for interacting with Gogs API."""

    CONFIGFILE = str(Path(__file__).parent / Path(__file__).stem) + ".ini"
    CONFIG = configset(CONFIGFILE)

    @classmethod
    def setup_parser(cls):
        subparsers = cls.parser.add_subparsers(dest='command', required=True)

        # REPO subparser
        repo_parser = subparsers.add_parser('repo', help='Repository operations', formatter_class=CustomRichHelpFormatter)
        repo_parser.add_argument('-a', '--add', metavar='REPO_NAME', help='Create new repository')
        repo_parser.add_argument('-l', '--list', action='store_true', help='List repositories')
        repo_parser.add_argument('-rm', '--remove', metavar='REPO_NAME', help='Remove repository')
        repo_parser.add_argument('-m', '--migrate', metavar='REPO_NAME', help='Migrate/clone repository from another server (gogs/gitea/github/etc)')
        repo_parser.add_argument('-n', '--name', metavar='REPO_NAME', help='Saved repository name for migration')

    @classmethod
    def usage(cls):
        cls.parser = argparse.ArgumentParser(
            description="Gogs CLI - Interact with Gogs API",
            formatter_class=CustomRichHelpFormatter
        )
        cls.parser.add_argument('-u', '--username', help='Gogs username')
        cls.parser.add_argument('-p', '--password', help='Gogs password')
        cls.parser.add_argument('--api', help='Gogs API key', default=cls.CONFIG.get_config('api', 'key', "c895e3636e813df4dbe9d01aed4bff0e14fc99b5"))
        cls.parser.add_argument('--url', help='Gogs API endpoint', default=cls.CONFIG.get_config('api', 'url', "http://gogs.container.com/api/v1"))
        cls.setup_parser()
        if len(sys.argv) == 1:
            cls.parser.print_help()
            return
        args = cls.parser.parse_args()
        cls.handle_args(args)

    @classmethod
    def handle_args(cls, args):
        if args.command == 'repo':
            if args.add:
                cls.create_repo(args)
            elif args.list:
                cls.list_repos(args)
            elif args.remove:
                cls.remove_repo(args)
            elif args.migrate:
                repo_name = args.name or args.migrate.split('/')[-1]
                cls.migrate_repo(args, repo_name, args.migrate)
            else:
                console.print("⚠️ [red]No repo action specified.[/]")
                sys.exit(1)
        else:
            console.print("❌ [red]Unknown command.[/]")
            sys.exit(1)

    @classmethod
    def migrate_repo(cls, args, repo_name, remote_url):
        """
        Migrate/clone repository from another server (gogs/gitea/github/etc) using Gitea API.
        """
        console.print(f"🚩 [#FFFF00]Migrating repository[/] [bold #00FFFF]'{repo_name}'[/] from [bold #00FFAA]{remote_url}[/]...")
        url = f"{args.url}/repos/migrate"
        auth, headers = cls.get_auth_headers(args)
        data = {
            "clone_addr": remote_url,
            "uid": None,  # will be filled below
            "repo_name": repo_name,
            "mirror": False,
            "private": False
        }
        # Get current user id (uid)
        user_url = f"{args.url}/user"
        try:
            r = requests.get(user_url, auth=auth, headers=headers)
            console.print(f"🔍 [#00FFAA]Getting user info from[/] [#FFFF00]{user_url}[/] [#FFFF00]\[{r.status_code}][/]")
            if r.status_code == 200:
                user = r.json()
                data["uid"] = user.get("id")
            else:
                console.print(f"\n❌ [red]Failed to get user info:[/] [white on blue]{r.status_code}[/] [#FFAA00{r.text}[/]")
                return
        except Exception as e:
            console.print(f"\n❌ [red]Error [1]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()
            return

        try:
            r = requests.post(url, auth=auth, headers=headers, json=data)
            console.print(f"🔄 [#00FFAA]Migrating repository to[/] [#FFFF00]{url}[/] [#FFFF00]\[{r.status_code}][/]")
            if r.status_code in (201, 200):
                console.print(f"⚠️ [#00FFFF]Repository[/] [#FFFF00]'{repo_name}'[/] [#00FFFF]migrated successfully from[/] [#00FFAA]{remote_url}.[/]")
            else:
                console.print(f"❌ [red]Failed to migrate repo:[/] [#FFFF00]{r.status_code}[/] [#00FFFF]{r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [2]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()
            
    @classmethod
    def get_auth_headers(cls, args):
        api_key = args.api or cls.CONFIG.get_config('api', 'key', "c895e3636e813df4dbe9d01aed4bff0e14fc99b5")
        headers = {'Authorization': f'token {api_key}'} if api_key else {}
        auth = None
        if not api_key:
            auth = (
                args.username or cls.CONFIG.get_config('auth', 'username'),
                args.password or cls.CONFIG.get_config('auth', 'password')
            )
        return auth, headers

    @classmethod
    def get_current_user(cls, args):
        """
        Take user username related to API_Key/Token.
        """
        url = f"{args.url}/user"
        _, headers = cls.get_auth_headers(args)
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                user = r.json()
                return user.get("login") or user.get("username")
            else:
                console.print(f"❌ [red]Failed to get current user: {r.status_code} {r.text}[/]")
                return None
        except Exception as e:
            console.print(f"❌ [red]Error [3]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()
            return None
        
    @classmethod
    def create_repo(cls, args):
        url = f"{args.url}/user/repos"
        auth, headers = cls.get_auth_headers(args)
        data = {"name": args.add}
        try:
            r = requests.post(url, auth=auth, headers=headers, json=data)
            if r.status_code == 201:
                console.print(f"✅ [green]Repository '{args.add}' created successfully.[/]")
            else:
                console.print(f"❌ [red]Failed to create repo: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [4]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()

    @classmethod
    def list_repos(cls, args):
        url = f"{args.url}/user/repos"
        auth, headers = cls.get_auth_headers(args)
        r = None
        try:
            r = requests.get(url, auth=auth, headers=headers)
            if r.status_code == 200:
                repos = r.json()
                if repos:
                    console.print("🔄 [bold green]Repositories:[/]")
                    for repo in repos:
                        console.print(f"- {repo['name']}")
                else:
                    console.print("⚠️ [yellow]No repositories found.[/]")
            else:
                console.print(f"❌ [red]Failed to list repos: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [5]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']:
                console.print_exception()
                console.log(f"❌ [red]Error [5]:[/] [white on blue]{e}[/] : [black on green]{r.content if r else None}[/]")
                clipboard.copy(r.content.decode()) if r else None

    @classmethod
    def remove_repo(cls, args):
        # Take a username from Token/API_Key
        owner = cls.get_current_user(args)
        if not owner:
            console.print("\n❌ [red]Cannot determine owner from api_key.[/]")
            return
        url = f"{args.url}/repos/{owner}/{args.remove}"
        _, headers = cls.get_auth_headers(args)
        try:
            r = requests.delete(url, headers=headers)
            if r.status_code == 204:
                console.print(f"🚩 [green]Repository '{args.remove}' deleted successfully.[/]")
            elif r.status_code == 404:
                console.print(f"⚠️ [yellow]Repository '{args.remove}' not found.[/]")
            else:
                console.print(f"❌ [red]Failed to delete repo: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [6]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()
            
    @classmethod
    def remove_repo2(cls, args):
        # Cari owner repo dari list repo
        auth, headers = cls.get_auth_headers(args)
        list_url = f"{args.url}/user/repos"
        try:
            r = requests.get(list_url, auth=auth, headers=headers)
            if r.status_code == 200:
                repos = r.json()
                owner = None
                for repo in repos:
                    if repo['name'] == args.remove:
                        owner = repo['owner']['username']
                        break
                if not owner:
                    console.print(f"[yellow]Repository '{args.remove}' not found in your account.[/]")
                    return
                url = f"{args.url}/repos/{owner}/{args.remove}"
                print("DELETE URL:", url)
                r = requests.delete(url, auth=auth, headers=headers)
                if r.status_code == 204:
                    console.print(f"[green]Repository '{args.remove}' deleted successfully.[/]")
                elif r.status_code == 404:
                    console.print(f"[yellow]Repository '{args.remove}' not found.[/]")
                else:
                    console.print(f"[red]Failed to delete repo: {r.status_code} {r.text}[/]")
            else:
                console.print(f"[red]Failed to list repos: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [7]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()
            
    @classmethod
    def remove_repo1(cls, args):
        url = f"{args.url}/repos/{args.username}/{args.remove}"
        auth, headers = cls.get_auth_headers(args)
        try:
            r = requests.delete(url, auth=auth, headers=headers)
            if r.status_code == 204:
                console.print(f"[green]Repository '{args.remove}' deleted successfully.[/]")
            elif r.status_code == 404:
                console.print(f"[yellow]Repository '{args.remove}' not found.[/]")
            else:
                console.print(f"[red]Failed to delete repo: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"❌ [red]Error [8]:[/] [white on blue]{e}[/]")
            if os.getenv('TRACEBACK') and os.getenv('TRACEBACK').lower() in ['1', 'true']: console.print_exception()

if __name__ == "__main__":
    CLI.usage()
