# -*- coding: utf-8 -*-
#
# Documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).

import sys, os, time
sys.path.append(os.path.abspath('tools/sphinxext'))


# General configuration
# ---------------------

# General substitutions.
project = 'Mod_python'
copyright = '1990-%s, Apache Software Foundation, Gregory Trubetskoy' % time.strftime('%Y')

# The default replacements for |version| and |release|.
#
# The short X.Y version.
# version = '2.6'
# The full version, including alpha/beta/rc tags.
# release = '2.6a0'

# version
import subprocess
v, r = subprocess.check_output(
    os.path.dirname(__file__) + "/../dist/version.sh", encoding='ASCII'
).rsplit('.', 1)
version, release = v, v+'.'+r

# Ignore .rst in Sphinx its self.
exclude_trees = ['tools/sphinx']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True


# Options for HTML output
# -----------------------

html_theme = 'default'
html_theme_options = {'collapsiblesidebar': True}

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, filenames relative to this file.
html_sidebars = {
    'index': 'indexsidebar.html',
}

# Output file base name for HTML help builder.                                                                                                                                                            
htmlhelp_basename = 'mod_python' + release.replace('.', '')

# Split the index
html_split_index = True


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
_stdauthor = r'Gregory Trubetskoy'
latex_documents = [
    ('contents', 'contents.tex',
     'Mod_python Documentation', _stdauthor, 'manual'),
]

# Documents to append as an appendix to all manuals.
latex_appendices = ['about', 'license', 'copyright']

# Get LaTeX to handle Unicode correctly
latex_elements = {'inputenc': r'\usepackage[utf8x]{inputenc}', 'utf8extra': ''}
