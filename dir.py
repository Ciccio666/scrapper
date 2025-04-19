import os

for root, dirs, files in os.walk(".", topdown=True):
    for name in files:
        print(os.path.relpath(os.path.join(root, name)))
