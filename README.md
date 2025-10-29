# Azure Boards: Sort Sprint Backlog

Sorts the work items on the Sprint Board/Backlog based on certain criteria.

Hosted at: [https://github.com/Sidelobe/AzureBoards-SortSprintBacklog](https://github.com/Sidelobe/AzureBoards-SortSprintBacklog)

## Configuration
Edit the `config.yaml` with your project details.

- `Organization`
- `Project`
- `Team`
- `Personal Access Token (PAT)` from Azure DevOps with these permissions:
    - Work Item:  Read & Write
    - Project & Team:  Read & Write
- `field_priority` default is `"Microsoft.VSTS.Common.Priority"`
- `field_stackrank` default is `"Microsoft.VSTS.Common.StackRank"`

## Running in a virtual python environment
Tested on macos, with python3 installed through `brew`

Create a virtual environment e.g. 'RaindropTest' and activate it:

```bash
python -m venv AzureBacklogSorter
source AzureBacklogSorter/bin/activate
```

Then install the required packages for the dependencies via PIP as required with: `pip install -r requirements.txt`.

NOTE: This script uses `tkinter`, which is installed on OS level, not through PIP. On macos, this can be installed with brew: `brew install python-tk`


## Packaging into a Standalone Application (optional)

1. First, install `pyinstaller` in the virtual environment: `pip install pyinstaller`

1. Then, run: `pyinstaller AzureBacklogSorter.spec sort_sprint_backlog.py`, which should produce an app (when running on macos) in the `dist` folder.

1. (optional) install `brew install create-dmg` to create a `.dmg`.

For convenience, the bash script `build_and_package.sh` can be used to combine all of the above steps.
   



Icon used:
<a href="https://www.flaticon.com/free-icons/ascending" title="ascending icons">Ascending icons created by Infinite Dendrogram - Flaticon</a>