import argparse
import os, sys
 
def processData(args, data):
    if args.tokenize:
        l.lexer.input(data)
        while True:
            tok = l.lexer.token()
            if not tok: break
            print tok
    elif args.compile:
        print l.parser.parse(data)

if __name__ == "__main__":
    path = os.path.dirname(os.path.dirname(__file__))
    if path not in sys.path:
        sys.path.append(path)
    
    import dcpu16.compiler as l

    parser = argparse.ArgumentParser(description='A compiler that turns c code to dcpu16 assembly code.')
    parser.add_argument('file', metavar='file', help='The file to tokenize or compile')
    parser.add_argument('--tokenize', action='store_true', help='Tokenize a file or from stdin')
    parser.add_argument('--compile', action='store_true', help='Compile a file or from stdin')
    
    args = parser.parse_args()
    
    if args.file:
        processData(args, open(args.file).read())
    else:
        file = open(sys.stdin)
        while True:
            processData(args, file.read())
 