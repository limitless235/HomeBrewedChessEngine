from setuptools import setup, find_packages

setup(
    name="chess_engine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "python-chess",
    ],
    python_requires=">=3.9",
)
