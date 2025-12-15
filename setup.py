from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="maestro-ai",
    version="1.2.1",
    author="Seppo Pakonen",
    author_email="seppo.pakonen@gmail.com",
    description="Maestro - AI Task Management & Orchestration CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/maestro",
    packages=find_packages(),
    py_modules=['session_model', 'engines'],  # Include the modules that main.py imports
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "maestro=maestro:main",
        ],
    },
    install_requires=[
        # Add any dependencies here if needed
        # For now, no external dependencies beyond standard library
        "toml>=0.10.0",
        "pyfiglet>=0.8.0",
        "textual>=0.40.0",
    ],
)