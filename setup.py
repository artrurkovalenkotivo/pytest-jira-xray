from setuptools import setup


def read_file(fname):
    with open(fname) as f:
        return f.read()


setup(
    name='pytest-xray-sync',
    version="0.0.1",
    url="https://github.com/artrurkovalenkotivo/pytest-jira-xray",
    author='Artur',
    author_email="",
    description="pytest plugin to integrate tests with JIRA XRAY",
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    packages=[
        'pytest_xray',
    ],
    package_dir={'pytest_xray': 'pytest_xray'},
    install_requires=[
        'pytest>=3.6',
        'requests',
    ],
    include_package_data=True,
    entry_points={'pytest11': ['pytest-xray-sync = pytest_xray.conftest']},
)
