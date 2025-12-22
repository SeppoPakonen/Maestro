"""
Setup for the Codex wrapper module.
"""
from setuptools import setup, find_packages

setup(
    name="maestro-codex-wrapper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pexpect>=4.8.0",
    ],
    author="Maestro Team",
    description="Codex CLI Loop wrapper for Maestro",
    python_requires=">=3.7",
)