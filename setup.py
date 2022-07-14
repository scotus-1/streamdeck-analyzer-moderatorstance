from setuptools import setup, find_packages

setup(
    name='streamdeck-analyzer-moderatorstance',
    version='0.0.0',
    py_modules=find_packages(),
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'analyzer = src.main:cli',
        ],
    },
)
