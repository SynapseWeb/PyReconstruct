import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Open a jser file in PyReconstruct')
    parser.add_argument('-f', '--filename', type=str, required=False, default=None, help='The file path for the jser')
    parser.add_argument('--update', action='store_true', help='Update PyReconstruct')
    args = parser.parse_args()

    if args.update:
        update()
    else:
        open_file(args.filename)

def open_file(filename):
    try:
        from PyReconstruct.run import runPyReconstruct
        runPyReconstruct(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")

def update():
    
    link = "git+https://github.com/synapseweb/pyreconstruct@test/pip-updating"
    
    cmd_uninstall = f"pip uninstall --yes PyReconstruct"
    cmd_reinstall = f"pip install {link}"
    
    subprocess.run(cmd_uninstall.split(" "))
    subprocess.run(cmd_reinstall.split(" "))

if __name__ == '__main__':
    main()
