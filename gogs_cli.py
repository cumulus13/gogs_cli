#!/usr/bin/env python

import requests
import argparse
from pathlib import Path
from rich.console import Console
from rich_argparse import RichHelpFormatter, _lazy_rich as rr
from typing import ClassVar
import sys
from configset import configset

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

    CONFIGFILE = str(Path(__file__).parent / 'gogs_cli.ini')
    CONFIG = configset(CONFIGFILE)

    @classmethod
    def setup_parser(cls):
        subparsers = cls.parser.add_subparsers(dest='command', required=True)

        # REPO subparser
        repo_parser = subparsers.add_parser('repo', help='Repository operations')
        repo_parser.add_argument('-a', '--add', metavar='REPO_NAME', help='Create new repository')
        repo_parser.add_argument('-l', '--list', action='store_true', help='List repositories')

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
            else:
                console.print("[red]No repo action specified.[/]")
                sys.exit(1)
        else:
            console.print("[red]Unknown command.[/]")
            sys.exit(1)

    @classmethod
    def create_repo(cls, args):
        url = f"{args.url}/user/repos"
        api_key = args.api or cls.CONFIG.get_config('api', 'key', "c895e3636e813df4dbe9d01aed4bff0e14fc99b5")
        headers = {'Authorization': f'token {api_key}'} if api_key else {}
        auth = None
        if not api_key:
            auth = (args.username or cls.CONFIG.get_config('auth', 'username'), args.password or cls.CONFIG.get_config('auth', 'password'))
        data = {"name": args.add}
        try:
            r = requests.post(url, auth=auth, headers=headers, json=data)
            if r.status_code == 201:
                console.print(f"[green]Repository '{args.add}' created successfully.[/]")
            else:
                console.print(f"[red]Failed to create repo: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

    @classmethod
    def list_repos(cls, args):
        url = f"{args.url}/user/repos"
        api_key = args.api or cls.CONFIG.get_config('api', 'key', 'c895e3636e813df4dbe9d01aed4bff0e14fc99b5')
        headers = {'Authorization': f'token {api_key}'} if api_key else {}
        auth = None
        if not api_key:
            auth = (args.username or cls.CONFIG.get_config('auth', 'username'), args.password or cls.CONFIG.get_config('auth', 'password'))
        try:
            r = requests.get(url, auth=auth, headers=headers)
            if r.status_code == 200:
                repos = r.json()
                if repos:
                    console.print("[bold green]Repositories:[/]")
                    for repo in repos:
                        console.print(f"- {repo['name']}")
                else:
                    console.print("[yellow]No repositories found.[/]")
            else:
                console.print(f"[red]Failed to list repos: {r.status_code} {r.text}[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

if __name__ == "__main__":
    CLI.usage()