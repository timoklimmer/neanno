from setuptools import setup

setup(
    name="neanno",
    url="https://github.com/timoklimmer/neanno",
    author="Timo Klimmer",
    author_email="timo.klimmer@microsoft.com",
    packages=["neanno"],
    install_requires=["PyQt5", "pandas", "spacy"],
    version="0.1",
    license="MIT",
    description="Yet another text annotation tool.",
    long_description=open("README.txt").read(),
    scripts=["neanno.py"],
    include_package_data=True,
)
