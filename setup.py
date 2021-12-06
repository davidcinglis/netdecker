import setuptools
import site
import sys
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="netdecker",
    version="0.0.1",
    author="David Inglis",
    author_email="davidcinglis@gmail.com",
    description="Creates importable decklists from MTG deck images.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/davidcinglis/decklist-ocr",
    project_urls={
        "Bug Tracker": "https://github.com/davidcinglis/decklist-ocr/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU GPLv3",
        "Operation System :: OS Independent",
    ],
    package_dir={"": "netdecker"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)