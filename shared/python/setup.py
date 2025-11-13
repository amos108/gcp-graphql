"""Setup script for playground_sdk"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent.parent.parent / 'README.md'
long_description = readme_file.read_text() if readme_file.exists() else ''

setup(
    name='playground-sdk',
    version='0.1.0',
    description='SDK for GCP Microservices Playground',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='you@example.com',
    url='https://github.com/yourusername/gcp-graphql',
    packages=find_packages(),
    install_requires=[
        'httpx>=0.25.0',
        'opentelemetry-api>=1.21.0',
        'opentelemetry-sdk>=1.21.0',
        'opentelemetry-exporter-cloud-trace>=1.6.0',
        'python-dotenv>=1.0.0',
    ],
    python_requires='>=3.11',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
