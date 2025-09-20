#!/usr/bin/env python3

from setuptools import setup, find_packages
from pathlib import Path
import os
import shutil
import traceback

NAME = "gogs_cli"
this_directory = os.path.abspath(os.path.dirname(__file__))

if (Path(__file__).parent / '__version__.py').is_file():
    shutil.copy(str((Path(__file__).parent / '__version__.py')), os.path.join(this_directory, NAME, '__version__.py'))
    
# Read the contents of README file
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
def get_version():
    """
    Get the version.
    Version is taken from the __version__.py file if it exists.
    The content of __version__.py should be:
    version = "0.33"
    """
    try:
        version_file = Path(__file__).parent / "__version__.py"
        if not version_file.is_file():
            version_file = Path(__file__).parent / NAME / "__version__.py"
        if version_file.is_file():
            with open(version_file, "r") as f:
                for line in f:
                    if line.strip().startswith("version"):
                        parts = line.split("=")
                        if len(parts) == 2:
                            return parts[1].strip().strip('"').strip("'")
    except Exception as e:
        if os.getenv('TRACEBACK') and os.getenv('TRACEBACK') in ['1', 'true', 'True']:
            print(traceback.format_exc())
        else:
            print(f"ERROR: {e}")

    return "0.0.0"

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
else:
    # Fallback requirements
    requirements = [
        'aiohttp>=3.8.0',
        'rich>=13.0.0',
        'rich-argparse>=1.0.0',
        'configset>=2.0.0',
        'clipboard>=0.0.4'
    ]

setup(
    name="gogs-cli",
    version=get_version(),
    author="Hadi Cahyadi",
    author_email="cumulus13@gmail.com",
    description="A high-performance, async command-line interface for interacting with Gogs Git repositories",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cumulus13/gogs_cli",
    project_urls={
        "Bug Tracker": "https://github.com/cumulus13/gogs_cli/issues",
        "Documentation": "https://github.com/cumulus13/gogs_cli#readme",
        "Source Code": "https://github.com/cumulus13/gogs_cli",
    },
    packages=find_packages(),
    py_modules=['gogs_cli'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.7",
    install_requires=[
        'aiohttp>=3.8.0',
    ],
    extras_require={
        'full': [
            'rich>=13.0.0',
            'rich-argparse>=1.0.0',
            'configset>=2.0.0',
            'clipboard>=0.0.4',
        ],
        'rich': [
            'rich>=13.0.0',
            'rich-argparse>=1.0.0',
        ],
        'config': [
            'configset>=2.0.0',
        ],
        'clipboard': [
            'clipboard>=0.0.4',
        ],
    },
    entry_points={
        'console_scripts': [
            'gogs-cli=gogs_cli:main',
            "gogs=gogs_cli:main",
        ],
    },
    keywords=[
        'gogs',
        'gitea', 
        'git',
        'cli',
        'async',
        'repository',
        'api',
        'command-line',
        'version-control'
    ],
    include_package_data=True,
    zip_safe=False,
)