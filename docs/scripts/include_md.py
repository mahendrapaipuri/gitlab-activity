#!/usr/bin/env python3
# Script to include the README files in the repository into docusaurus src
import re
from pathlib import Path


# Root of the repository
repo_root = Path(__file__).resolve().parent.parent.parent.resolve()

# Docusaurus docs path
docs_path = repo_root.joinpath('docs', 'website', 'docs')

# Iterate over all files in folder
for f in docs_path.glob('**/*.md'):
    # Read contents
    content = f.read_text(encoding='utf-8')

    # Get path from marker to include the file
    path_match = re.search('^<!-- (.*) -->$', content, re.M)

    # If there is no match continue
    if not path_match:
        continue

    path = path_match.group(1)
    fpath = docs_path.joinpath(path)

    # Read contents from path
    new_content = fpath.read_text(encoding='utf-8')

    # Split old content at marker and update it with new_content
    marker = f'<!-- {path} -->'
    content = content.split(marker)[0].strip('\n')
    new_content = format(f'{content}\n\n{marker}\n\n{new_content}')

    # Finally write the new content back to f
    print(f'Updating md file at {f}')  # noqa: T201
    f.write_text(new_content, encoding='utf-8')
