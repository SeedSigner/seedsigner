import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lumensigner",
    author="overcat",
    author_email="4catcode@gmail.com",
    description="Build an offline, airgapped Stellar signing device for less than $50!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LumenSigner/lumensigner",
    project_urls={
        "Bug Tracker": "https://github.com/LumenSigner/lumensigner/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.7",
    package_data={
        "lumensigner": [
            "resources/**",
        ]
    },
    entry_points={
        "console_scripts": [
            "lumensigner = lumensigner.cli:start",
        ]
    },
)
