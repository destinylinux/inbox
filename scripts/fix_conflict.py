#!/usr/bin/env python3
import re

with open('index.html') as f:
    c = f.read()

# Remove all conflict markers (keep OURS side)
c = re.sub(r'<<<<<<< HEAD\n=======\n', '', c)
c = re.sub(r'>>>>>>> [^\n]+', '', c)

# Fix up extra blank lines
c = c.replace('\n\n\n', '\n\n')

opens = c.count('<div')
closes = c.count('</div>')
print(f'Divs: {opens}/{closes} diff={opens-closes}')
print(f'Has conflict markers: {("<<<<<<<" in c) or (">>>>>>>" in c)}')
print(f'Has V11 page: {"pageV11" in c}')
print(f'Has V11 tab: {"tab-l2" in c and "V11" in c}')

with open('index.html', 'w') as f:
    f.write(c)
print("Done!")
