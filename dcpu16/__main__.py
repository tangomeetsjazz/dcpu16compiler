import argparse
import os, sys

if __name__ == "__main__":
    path = os.path.dirname(os.path.dirname(__file__))
    if path not in sys.path:
        sys.path.append(path)
    
    import dcpu16.compiler as l

    parser = argparse.ArgumentParser(description='A compiler that turns python code to dcpu16 assembly code.')
    parser.add_argument('file', metavar='file', help='The file to tokenize or compile')
    
    args = parser.parse_args()
    
    l.parse(open(args.file).read())
 