import ast
import re

from setuptools import find_packages, setup

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("graphene_umongo/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

requirements = [
    "graphene",
    "umongo",
    "six",
    "singledispatch",
]

tests_require = [
    "pytest",
    "mock",
    "pytest",
]

setup(
    name="graphene-umongo",
    version=version,
    description="Graphene umongo integration",
    long_description=open("README.md").read(),
    url="https://github.com/gerasim13/graphene-umongo",
    author="Pavel Litvinenko",
    author_email="digitaldistortion@ya.ru",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords="api graphql protocol rest relay graphene",
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    extras_require={
        "dev": [
            "coveralls",
            "pre-commit",
        ],
        "test": tests_require,
    },
    tests_require=tests_require,
)
