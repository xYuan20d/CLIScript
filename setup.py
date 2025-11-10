from setuptools import setup, find_packages

# 读取 README.md 作为长描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取 requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="cliscript",
    version="0.1.1",
    author="xYuan20d",
    author_email="xiaoyy20d@gmail.com",
    description="A Domain Specific Language for building CLI applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xYuan20d/CLIScript",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cliscript=cliscript.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "cliscript": ["*.py"],
    },
    keywords="cli, dsl, argparse, command-line, parser",
    project_urls={
        "Bug Reports": "https://github.com/xYuan20d/CLIScript/issues",
        "Source": "https://github.com/xYuan20d/CLIScript",
        "Documentation": "https://github.com/xYuan20d/CLIScript/README.md",
    },
)