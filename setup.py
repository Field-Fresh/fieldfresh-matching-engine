from setuptools import setup, find_packages

with open('requirements.txt') as f:
    deps = f.readlines()

setup(
    name='fieldFresh-matching-engine',
    version='0.1.0',
    description='matching engine for field fresh',
    install_requires = deps,
    packages=find_packages(exclude=['service', 'tests'])
)