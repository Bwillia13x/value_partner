from setuptools import setup, find_packages

setup(
    name='valueinvest_sdk',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.32',
    ],
)
