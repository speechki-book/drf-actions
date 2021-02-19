from setuptools import setup, find_packages
from codecs import open
from os import path


def readme():
    with open("README.md", "r") as infile:
        return infile.read()


classifiers = [
    # Pick your license as you wish (should match "license" above)
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
]
setup(
    name="drf_actions",
    version="0.1.1",
    description="Create event log with help triggers and send notify after create event",
    author="Pavel Maltsev",
    author_email="pavel@speechki.org",
    packages=find_packages(exclude=["tests*"]),
    url="https://github.com/speechki-book/drf-actions",
    license="MIT",
    keywords="django restframework drf events log",
    long_description=readme(),
    classifiers=classifiers,
    long_description_content_type="text/markdown",
    install_requires=[  # I get to this in a second
        "django>=2.2.19",
        "djangorestframework>=3.12.2",
        "django-model-utils>=4.0.0",
        "django-filter>=2.4.0",
        "celery",
    ],
    include_package_data=True,
)