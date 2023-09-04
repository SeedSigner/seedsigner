import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="seedsigner",
    version="0.7.0",
    author="SeedSigner",
    author_email="author@example.com",
    description="Build an offline, airgapped Bitcoin signing device for less than $50!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SeedSigner/seedsigner",
    project_urls={
        "Bug Tracker": "https://github.com/SeedSigner/seedsigner/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.6",
)
