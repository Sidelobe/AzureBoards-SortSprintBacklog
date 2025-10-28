#!/usr/bin/python3
"""
Python 3.x script to sort the Azure Sprint Backlog based on some criteria
"""

import sys # for sys.exit
import argparse
import requests
import base64
import yaml
from collections import namedtuple
import tkinter as tk
from tkinter import ttk

def main():
    parser = argparse.ArgumentParser(prog=None)
    parser.add_argument('config', help='Configuration file that contains c')
    parser.add_argument('--dryrun', action='store_true', help='Prints resulting order only, without making any modifications')
    args = parser.parse_args()

    if args.dryrun:
        print("--dryrun specified!")

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    # Sorter
    stackrank_sorter = StackRankSorter(config)

    # Start GUI
    iteration_selector = IterationSelectorGui(stackrank_sorter, args.dryrun)

def sort_work_item_table(work_item_ancestry_table):
        """
        Sort a work item table based on certain criteria. 
        TODO: make this generic, i.e. with "SortingCriterion_Type"
        """
        
        # --> This is for a customized CMMI process
        # Hierarchy: 
        # 1. Issues
        # 2. Bugs
        # 3. Planning Items - order of (grand)parent Epic's (if applicable) stack rank
        # 4. Any other work items (Requirements, Activities):
        #          - grandparent Epic's stack rank
        #          - then parent Feature priority
        #          - then work item's priority  TODO: consider using item's stack rank instead

        work_item_ancestry_table.sort(key=lambda x: (x.item_type == 'Issue', 
                                                    x.item_type == 'Bug', 
                                                    x.item_type == 'Planning Item' and x.grandparent_stackrank is not None and x.grandparent_stackrank, 
                                                    x.grandparent_stackrank is not None and x.grandparent_stackrank,
                                                    x.parent_prio is not None and x.parent_prio,
                                                    x.item_prio is not None and x.item_prio),
                                    reverse=False)

        # for some reason, we need to reverse separately at the end, not in initial sort
        work_item_ancestry_table.reverse()

class IterationSelectorGui(tk.Tk):
    def __init__(self, stackrank_sorter, dryRun):
        super().__init__()
        
        self.stackrank_sorter = stackrank_sorter
        self.dryRun = dryRun

        self.title("Choose Iteration")

        # Configure DropDown: Get Iterations and 'Current iteration' (depends on date)
        self.iteration_prefix = f"{stackrank_sorter.project}\\"
        iteration_paths = stackrank_sorter.get_iterations()
        iteration_paths = [item.removeprefix(self.iteration_prefix) for item in iteration_paths]
        current_iteration = stackrank_sorter.get_iterations(getCurrentIterationOnly=True)[0]
        current_iteration = current_iteration.removeprefix(self.iteration_prefix)

        self.dropdown = ttk.Combobox(self, text='Iteration', values=iteration_paths)
        self.dropdown.pack(padx=5, pady=5, fill="x")
        self.dropdown.set(current_iteration)

        self.sort_button = tk.Button(self, text="Sort Sprint Backlog", command=self.sort_selected_iteration)
        self.sort_button.pack()

        self.feedback = tk.Label(self, text="")
        self.feedback.pack(padx=5, pady=5, fill="x")
        
        # Window size & position
        w = 350
        h = 100
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.tk.mainloop()

    def sort_selected_iteration(self):
        selected_iteration = self.dropdown.get()
        selected_iteration_path = f"{self.iteration_prefix}{selected_iteration}"
        self.stackrank_sorter.sort_backlog(selected_iteration_path, self.dryRun)
        self.feedback.config(text=self.stackrank_sorter.resultText)

class StackRankSorter():
    def __init__(self, config):
        self.organization = config['organization']
        self.project = config['project']
        self.team = config['team']
        pat = config['pat']
        self.encoded_pat = base64.b64encode(f":{pat}".encode()).decode()
        self.priority_field = config['field_priority']
        self.stackrank_field= config['field_stackrank']
        self.resultText = "" # to give feedback to user

    def sort_backlog(self, iteration_path, dryRun=False):
        # Get hierarchy as 'family tree' (includes grandparent's stack rank)
        work_item_ancestry_table = self.get_work_item_ancestrytable(iteration_path)
        if work_item_ancestry_table is None:
            self.resultText = "Nothing to sort: Iteration contains no work items."
        else:
            sort_work_item_table(work_item_ancestry_table)

            # DryRun: Pretty-print results instead of applying order
            if dryRun:
                StackRankSorter.pretty_print_table(work_item_ancestry_table)
                return
            
            # Update Stack Rank to match new order
            work_item_ids_ordered = [item.item_id for item in work_item_ancestry_table]
            self.update_stack_rank(work_item_ids_ordered)

            self.resultText = "Backlog items reordered successfully."

    def get_iterations(self, getCurrentIterationOnly=False):
        """
        Returns a list of all iterations, obtained through the REST API.
        """

        headers_query = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.encoded_pat}"
        }

        # Get all available iterations
        url = f"https://dev.azure.com/{self.organization}/{self.project}/{self.team}/_apis/work/teamsettings/iterations?$depth=3&api-version=7.1"
        if getCurrentIterationOnly:
            url += f"&$timeframe=current"
        
        response = requests.get(url, headers=headers_query)
        return [item["path"] for item in response.json()['value']]

    def get_work_item_ancestrytable(self, iteration_path):
        """
        Get work items in the sprint and their details including parent/grandparent links with prios and stack rank
        """
        
        headers_query = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.encoded_pat}"
        }

        # Step 1: Get work items in the sprint
        # https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax?view=azure-devops
        query_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/wiql?api-version=7.0"
        query = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.IterationPath] = '{iteration_path}'
            """
        }
        response = requests.post(query_url, json=query, headers=headers_query)
        work_item_ids = [item["id"] for item in response.json()["workItems"]]

        if not work_item_ids: 
            return None # Iteration contains no work items
        
        # Step 2: Get details including parent links and stack rank
        url = f"https://dev.azure.com/{self.organization}/_apis/wit/workitemsbatch?api-version=7.0"
        details_query = {
            "ids": work_item_ids,
            "fields": ["System.Id", "System.WorkItemType", "System.Title", "System.Parent", f"{self.priority_field}"],
            "expand": "Relations"
        }
        work_item_details = requests.post(url, json=details_query, headers=headers_query).json()
        
        # Step 3: Get parents and grandparents
        fields = ('item_id', 'item_title', 'item_type', 'item_prio', 'parent', 'parent_prio', 'grandparent', 'grandparent_title', 'grandparent_stackrank')
        AncestryInfoTable = namedtuple('AncestryInfoTable', fields, defaults=(None,) * len(fields))
        work_item_ancestry_table = []
        
        for i, item in enumerate(work_item_details['value']):
            item_id = item['id']
            item_type = None
            if 'System.WorkItemType' in item['fields']:
                item_type = item['fields']['System.WorkItemType']

            item_title = ""
            if 'System.Title' in item['fields']:
                item_title = item['fields']['System.Title']

            item_prio = None
            if self.priority_field in item['fields']:
                item_prio = item['fields'][self.priority_field]

            if 'System.Parent' not in item['fields']:
                work_item_ancestry_table.append(AncestryInfoTable(item_id=item_id, item_title=item_title, item_type=item_type, item_prio=item_prio))
                continue # safely skip items without parent

            parent = item['fields']['System.Parent']
            parent_query = {
                "ids": [parent],
                "fields": ["System.Id", "System.Title", "System.Parent", "System.IterationPath", self.priority_field],
                "expand": "Relations"
            }
            item_parent_details = requests.post(url, json=parent_query, headers=headers_query).json()
            item_parent = item_parent_details['value'][0] # only one parent queried
            parent_prio = None
            if self.priority_field in item_parent['fields']:
                parent_prio = item_parent['fields'][self.priority_field]

            if 'System.Parent' not in item_parent['fields']:
                work_item_ancestry_table.append(AncestryInfoTable(item_id=item_id, item_title=item_title, item_type=item_type, item_prio=item_prio, 
                                                                parent=parent, parent_prio=parent_prio))
                continue # safely skip items without parent

            grandparent = item_parent['fields']['System.Parent']
            grandparent_query = {
                "ids": [grandparent],
                "fields": ["System.Id", "System.Title", "System.IterationPath", self.stackrank_field],
                "expand": "Relations"
            }
            item_grandparent_details = requests.post(url, json=grandparent_query, headers=headers_query).json()
            item_grandparent = item_grandparent_details['value'][0] # only one parent queried

            grandparent_title = ""
            if 'System.Title' in item_grandparent['fields']:
                grandparent_title = item_grandparent['fields']['System.Title']
            grandparent_stack_rank = None
            if self.stackrank_field in item_grandparent['fields']:
                grandparent_stack_rank = item_grandparent['fields'][self.stackrank_field]
            
            node = AncestryInfoTable(item_id=item_id, item_type=item_type, item_title=item_title, item_prio=item_prio, parent=parent, parent_prio=parent_prio, 
                                    grandparent=grandparent, grandparent_title=grandparent_title, grandparent_stackrank=grandparent_stack_rank)
            work_item_ancestry_table.append(node)

        return (work_item_ancestry_table)

    def update_stack_rank(self, work_item_ids_ordered):
        """
        Update the stack rank of the give work items so they reflect the given order
        """
        headers_patch = {
            "Content-Type": "application/json-patch+json",
            "Authorization": f"Basic {self.encoded_pat}"
        }

        for i, id in enumerate(work_item_ids_ordered):
            update_url = f"https://dev.azure.com/{self.organization}/_apis/wit/workitems/{id}?api-version=7.0"
            patch_data = [
                {
                    "op": "add",
                    "path": f"/fields/{self.stackrank_field}",
                    "value": 10000 + i  # or any ranking logic
                }
            ]
            r = requests.patch(update_url, json=patch_data, headers=headers_patch)
            if (r.status_code != 200):
                print(r.status_code)
                print(r.text)
                sys.exit(-1)

    @staticmethod
    def pretty_print_table(work_item_ancestry_table):
        """
        Pretty-Print the work item table, showing the corresponding grandparent epics
        """
        print("Resulting stack rank:\n")
        epics_section_started = False
        out = ""
        for i, item in enumerate(work_item_ancestry_table):
            if not epics_section_started and item.item_type in {"Requirement", "Activity"}:
                out += "-" * 160 + "\n"
                epics_section_started = True

            out += "\t" + str(i)
            out += "\t" + f"{item.item_type:<15}"
            out += "\t" + f"{item.item_title:<65}"

            if item.grandparent_title is not None: 
                out += "\t"
                if i > 1 and i < len(work_item_ancestry_table)-2:
                    previous_epic = work_item_ancestry_table[i-1].grandparent_title
                    next_epic = work_item_ancestry_table[i+1].grandparent_title
                    if item.grandparent_title != previous_epic:
                        out += "┌ " 
                    elif item.grandparent_title != next_epic:
                        out += "└ " 
                    else:
                        out += "│ "
                elif i < len(work_item_ancestry_table)-1:  
                    out += "└ "

                out += f"{item.grandparent_title:<65}"

            out += "\n"
            
        print(out)


if __name__ == "__main__":
    main()