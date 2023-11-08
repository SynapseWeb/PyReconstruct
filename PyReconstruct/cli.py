import argparse

def main():
    parser = argparse.ArgumentParser(description='Open a jser file in PyReconstruct')
    parser.add_argument('-f', '--filename', type=str, required=False, default=None, help='The file path for the jser')
    args = parser.parse_args()

    # Process the file opening logic
    open_file(args.filename)

def open_file(filename):
    try:
        from PyReconstruct.run import runPyReconstruct
        runPyReconstruct(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")

if __name__ == '__main__':
    main()