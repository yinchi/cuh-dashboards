"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# pylint: disable=C0103,W0622

import sys
sys.path.insert(0, '../../hpath/')

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'CUH NHS Trust: Dashboard Server'
copyright = '2023, Institute for Manufacturing, University of Cambridge'
author = 'Yin-Chi Chan'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.githubpages',
              'sphinx.ext.intersphinx',
              'sphinx.ext.napoleon',
              'sphinxcontrib.kroki']

autodoc_typehints_format = 'fully-qualified'
autoapi_add_toctree_entry = False
autoapi_member_order = 'bysource'

autodoc_default_options = {
    'member-order': 'groupwise',
    'exclude-members': 'model_config, model_fields'
}


# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
# napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True

templates_path = ['_templates']
exclude_patterns = []

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('http://pandas.pydata.org/docs/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'openpyxl': ('https://openpyxl.readthedocs.io/en/stable/', None),
    'salabim': ('https://www.salabim.org/manual/', None),
    'sphinx': ("https://www.sphinx-doc.org/en/master/", None),
    'pydantic': ("https://docs.pydantic.dev/latest/", None),
    'flask': ("https://flask.palletsprojects.com/en/latest/", None)
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 99,
}
html_context = {
  'display_github': True,
  'github_user': 'yinchi',
  'github_repo': 'cuh-dashboards',
  'github_version': 'main',
  'conf_py_path': "/documentation/source/"
}
