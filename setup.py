
# -*- coding: utf-8 -*-
from setuptools import setup

import codecs

with codecs.open('README.md', encoding="utf-8") as fp:
    long_description = fp.read()
INSTALL_REQUIRES = [
    'jsons<2.0.0,>=1.6.1',
    'numpy<2.0.0,>=1.22.1',
    'pandas<2.0.0,>=1.4.1',
    'python-dateutil<3.0.0,>=2.8.2',
    'requests<3.0.0,>=2.27.1',
    'Rx<4.0.0,>=3.2.0',
    'rxpy-backpressure<2.0.0,>=1.0.0',
    'solana~=0.25',
    'websocket-client<2.0.0,>=1.2.1',
    'zstandard<1.0.0,>=0.17.0',
    'pyserum>=0.5.0a0',
]

setup_kwargs = {
    'name': 'mango-explorer',
    'version': '3.4.8',
    'description': 'Python integration for https://mango.markets',
    'long_description': long_description,
    'license': 'MIT',
    'author': '',
    'author_email': 'pyz4 <pyz4>',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://mango.markets',
    'packages': [
        'mango',
        'mango.hedging',
        'mango.layouts',
        'mango.marketmaking',
        'mango.oracles',
        'mango.simplemarketmaking',
        'mango.marketmaking.orderchain',
        'mango.oracles.ftx',
        'mango.oracles.market',
        'mango.oracles.pythnetwork',
        'mango.oracles.stub',
    ],
    'package_data': {'': ['*']},
    'long_description_content_type': 'text/markdown',
    'install_requires': INSTALL_REQUIRES,
    'python_requires': '>=3.9,<3.11',

}


setup(**setup_kwargs)
