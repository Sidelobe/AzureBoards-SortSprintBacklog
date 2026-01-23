# Azure Boards: Sort Sprint Backlog

Sorts the work items on the Sprint Board/Backlog based on certain criteria.

Hosted at: [https://github.com/Sidelobe/AzureBoards-SortSprintBacklog](https://github.com/Sidelobe/AzureBoards-SortSprintBacklog)

## Information for End-Users

### Configuration
The app will not work out of the box. After installing via the `.dmg`, make sure to edit the `~/Library/Application Support/config.yml` file and add the corresponding configuration data so the app works with your Azure organization & project. This file will be created the first time the app started.

- In Finder, select `Go->Go to folder` or `Cmd+Shift+G` and enter `~/Library/Application Support` and then edit `config.yml` with your favourite text editor
- Fill out all fields according to your Azure Board settings and desired project.

### PAT - Personal Acccess Token
You need to create a `Personal Access Token (PAT)` in Azure DevOps with the following permissions:

- Work Item:  Read & Write
- Project & Team:  Read & Write