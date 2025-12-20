
import re
from setuptools import setup, find_namespace_packages


with open("README.md", "r") as f:
    long_description = f.read()

with open("ttgwlib/version.py") as f:
    version = re.search(r"VERSION = \"(.*?)\"", f.read()).group(1)

setup(
    name="ttgwlib",
    version=version,
    license="proprietary and confidential",
    url="https://bitbucket.org/tychetools/gw-library",
    project_urls={
        "Documentation": "",
        "Code": "https://bitbucket.org/tychetools/gw-library",
        "Issue tracker": "",
    },
    author="TycheTools",
    maintainer="TycheTools FW Team",
    maintainer_email="info@tychetools.com",
    description="TycheTools gateway library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=["ttgwlib", "ttgwlib.*"]),
    install_requires=[
        "pyserial==3.5",
        "cryptography==36.0.2",
        "packaging==24.2",
    ],
    extras_require={
        "boto3": ["boto3==1.20.12"],
        "jlink": ["pylink-square==0.11.1"],
    },
    python_requires=">=3.7",
)
