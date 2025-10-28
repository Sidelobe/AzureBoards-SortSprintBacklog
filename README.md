# Azure Boards: Sort Sprint Backlog

Sorts the work items on the Sprint Board/Backlog based on certain criteria.

Hosted at: [https://github.com/Sidelobe/AzureBoards-SortSprintBacklog](https://github.com/Sidelobe/AzureBoards-SortSprintBacklog)

## Configuration
Edit the `config.yaml` with your project details.

- `Organization`
- `Project`
- `Team`
- `Personal Access Token (PAT)` from Azure DevOps with access to:
    - Work Item Read & Write
    - Project & Team access
- `field_priority` default is `"Microsoft.VSTS.Common.Priority"`
- `field_stackrank` default is `"Microsoft.VSTS.Common.StackRank"`

## Running in a virtual python environment
Tested on macos, with python3 installed through `brew`

Create a virtual environment e.g. 'RaindropTest' and activate it:

```bash
python3 -m venv AzureSortBacklog
source AzureSortBacklog/bin/activate
```

Then install the required packages for the dependencies via PIP as required with: `pip install -r requirements.txt`.