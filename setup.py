"""Setup script for lm360 package."""

from pathlib import Path
from setuptools import setup, find_packages

readme = Path("README.md").read_text(encoding="utf-8")

setup(
    name="lm360",
    version="1.0.0",
    author="lm360 contributors",
    description="DeepCool LM360 AIO LCD control for Linux",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/PLACEHOLDER/lm360",
    packages=find_packages(exclude=["tests", "tests.*"]),
    scripts=["lm360-bin"],
    python_requires=">=3.10",
    install_requires=[
        "pyusb>=1.2.0",
        "psutil>=5.9.0",
        "Pillow>=9.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Hardware",
        "Topic :: System :: Monitoring",
    ],
    keywords="deepcool lm360 aio lcd driver hardware monitoring",
    project_urls={
        "Bug Reports": "https://github.com/PLACEHOLDER/lm360/issues",
        "Source": "https://github.com/PLACEHOLDER/lm360",
    },
)
