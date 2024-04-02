import argparse
import subprocess

try:
    
    from PyReconstruct.modules.constants import repo_info
    
except ModuleNotFoundError:

    repo_info = {"branch": "unknown", "commit": "unknown"}

def main():

    parser = argparse.ArgumentParser(description='Open a jser file in PyReconstruct')

    parser.add_argument('-f', '--filename', type=str, required=False, default=None, help='The file path for the jser')
    parser.add_argument('-u', '--update', action='store_true', help='Update PyReconstruct')
    parser.add_argument('-b', '--branch', action='store_true', help='Show current branch')
    parser.add_argument('-c', '--commit', action='store_true', help='Show current commit')
    parser.add_argument('-s', '--switch', type=str, required=False, default=None, help='Switch PyReconstruct branch')
    
    args = parser.parse_args()

    if args.update:
        
        update()
        
    elif args.branch:
        
        print(repo_info.get("branch"))
        
    elif args.commit:
        
        print(repo_info.get("commit"))
        
    elif args.switch:
        
        update(args.switch)
        
    else:
        
        open_file(args.filename)

def open_file(filename):
    try:
        from PyReconstruct.run import runPyReconstruct
        runPyReconstruct(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")

def validate_branch(requested_branch):

    repo = "https://github.com/synapseweb/pyreconstruct"
    cmd = f"git ls-remote --heads {repo} refs/heads/{requested_branch}"
    output = subprocess.run(cmd.split(" "), capture_output=True, text=True)

    return bool(output.stdout.strip())

def update(requested_branch=None):

    if requested_branch:

        if not validate_branch(requested_branch):
            print(f"Branch {requested_branch} does not exist.")
            return

    else:
    
        requested_branch = repo_info.get("branch")  # get current branch

        if requested_branch == "unknown":
            requested_branch = "main"
    
    link = f"git+https://github.com/synapseweb/pyreconstruct@{requested_branch}"

    ## Run two commands to easily install new dependencies
    
    cmd_uninstall = f"pip uninstall --yes PyReconstruct"
    cmd_reinstall = f"pip install {link}"
    
    subprocess.run(cmd_uninstall.split(" "))
    subprocess.run(cmd_reinstall.split(" "))

if __name__ == '__main__':
    main()
