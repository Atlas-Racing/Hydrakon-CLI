from setuptools import setup, find_packages

setup(
    name="hydrakon",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "rich"
    ],
    entry_points={
        "console_scripts": [
            "hydrakon=hydrakon.main:app",
            "hdk=hydrakon.main:app",
        ],
    },
)