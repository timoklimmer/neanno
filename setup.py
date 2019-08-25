import re

from setuptools import setup

import neanno

version = neanno.__version__

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="neanno",
    url="https://github.com/timoklimmer/neanno",
    author="Timo Klimmer",
    author_email="timo.klimmer@microsoft.com",
    packages=["neanno"],
    install_requires=requirements,
    version=version,
    license="MIT",
    description="Yet another text annotation tool.",
    long_description=open("README.txt").read(),
    scripts=["neanno.py"],
    include_package_data=True,
)
