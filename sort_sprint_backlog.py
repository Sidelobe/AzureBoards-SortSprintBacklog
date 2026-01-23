#!/usr/bin/python3
"""
Python 3.x script to sort the Azure Sprint Backlog based on some criteria
"""

import sys # for sys.exit
import os
import argparse
import requests
import base64
import json
import yaml
from collections import namedtuple
import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import messagebox

def main():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app 
        # path into variable _MEIPASS'.
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))


    parser = argparse.ArgumentParser(prog=None)
    parser.add_argument('--config', help='Configuration file that contains credentials and paths to access Azure Boards')
    parser.add_argument('--dryrun', action='store_true', help='Prints resulting order only, without making any modifications')
    args = parser.parse_args()

    if not args.config:
        print("No config file specified, trying default [config.yml]")
        print("(Application path is ", application_path, " looking for config file in directory ../Resources)")
        args.config = f"{application_path}/../Resources/config.yml"

    if args.dryrun:
        print("--dryrun specified!")

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    check_config(config)

    # Sorter
    stackrank_sorter = StackRankSorter(config)

    # DEBUG
    # args.dryrun = True

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
        # 2. 'Disruptions'
        # 3. Bugs
        # 4. 'Planning Items' - order of (grand)parent Epic's (if applicable) stack rank
        # 5. Any other work items (Requirements, 'Activities'):
        #          - grandparent Epic's stack rank
        #          - then parent Feature priority
        #          - then work item's priority  TODO: consider using item's stack rank instead

        work_item_ancestry_table.sort(key=lambda x: (x.item_type != 'Issue',  # NOTE: use != achieve desired result
                                                    x.item_type != 'Disruption', 
                                                    x.item_type != 'Bug', 
                                                    x.item_type != 'Planning Item' and x.grandparent_stackrank is not None and int(x.grandparent_stackrank), 
                                                    x.grandparent_stackrank is not None and int(x.grandparent_stackrank),
                                                    x.parent_prio is not None and int(x.parent_prio),
                                                    x.item_prio is not None and int(x.item_prio)),
                                    reverse=False)

class IterationSelectorGui(tk.Tk):
    def __init__(self, stackrank_sorter, cmdLineDryRun):
        super().__init__()
        
        self.title("Choose Iteration Backlog to sort")

        self.new_window = None
        self.stackrank_sorter = stackrank_sorter
        self.dryRun = tk.IntVar()
        self.dryRun.set(cmdLineDryRun)

        self.feedback = tk.Label(self, text="")
        
        # use a frame for the two labels
        frame = tk.Frame(self)
        frame.pack()
        self.labelNumEpics =    tk.Label(frame, text="", font=('TkDefaultFont', 14), fg="orange")
        self.labelNumFeatures = tk.Label(frame, text="", font=('TkDefaultFont', 14), fg="purple")
        self.labelNumEpics.grid(row=0, column=0, padx=15)
        self.labelNumFeatures.grid(row=0, column=1, padx=15)

        # Configure DropDown: Get Iterations and 'Current iteration' (depends on date)
        self.iteration_prefix = f"{stackrank_sorter.project}\\"
        iteration_paths = stackrank_sorter.get_iterations()
        if iteration_paths is None:
            self.feedback.config(text=self.stackrank_sorter.result_text)
            self.feedback.update()
            iteration_paths = []
            current_iteration = ""
        else:
            iteration_paths = [item.removeprefix(self.iteration_prefix) for item in iteration_paths]
            iterations = stackrank_sorter.get_iterations(getCurrentIterationOnly=True)
            if iterations is None:
                current_iteration = ""
                current_iteration_idx = 0
            else:
                current_iteration = iterations[0]
                current_iteration = current_iteration.removeprefix(self.iteration_prefix)
                current_iteration_idx = iteration_paths.index(current_iteration)

            # Restrict to 5 iterations before current iteration
            i = max(0, current_iteration_idx-5); # clamp to 0
            iteration_paths = iteration_paths[i:len(iteration_paths)]

        self.dropdown = ttk.Combobox(self, text='Iteration', values=iteration_paths)
        self.dropdown.bind('<<ComboboxSelected>>', self.select_dropdown)
        self.dropdown.pack(padx=5, pady=5, fill="x")
        self.dropdown.set(current_iteration)
     
        frameBottom = tk.Frame(self)
        frameBottom.pack()
        self.dryRunSelector = tk.Checkbutton(frameBottom, text="Dry Run", variable=self.dryRun, command=self.dryRunSelected)
        self.sort_button = tk.Button(frameBottom, text="Sort Sprint Backlog", command=self.sort_selected_iteration)
  
        self.sort_button.grid(row=0, column=0, padx=15)
        self.dryRunSelector.grid(row=0, column=1, padx=15)

        self.feedback.pack(padx=5, pady=5, fill="x")

        # Window size & position
        w = 350
        h = 130
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        
        self.tk.mainloop()

    def sort_selected_iteration(self):
        self.feedback.config(text="Sorting...")
        self.feedback.update()
        selected_iteration_path = self.get_selected_iteration_path()
        self.stackrank_sorter.sort_backlog(selected_iteration_path, self.dryRun.get())
        if self.dryRun.get():
            self.print_in_new_window(self.stackrank_sorter.result_dryRun)
            print(self.stackrank_sorter.result_dryRun) # print to console, too
       
        self.labelNumEpics.config(text=f"{self.stackrank_sorter.result_num_epics} Epics")
        self.labelNumFeatures.config(text=f"{self.stackrank_sorter.result_num_features} Features")
        self.feedback.config(text=self.stackrank_sorter.result_text)
    
    def select_dropdown(self, choice):
        self.labelNumEpics.config(text="")
        self.labelNumFeatures.config(text="")
        self.feedback.config(text="")
        if self.new_window:
            self.new_window.destroy()
        return "break"

    def get_selected_iteration_path(self):
        selected_iteration = self.dropdown.get()
        return f"{self.iteration_prefix}{selected_iteration}"
    
    def dryRunSelected(self):
        if not self.dryRun.get() and self.new_window:
            self.new_window.destroy()
    
    def print_in_new_window(self, text_to_display):
        if self.new_window is not None:
            self.new_window.destroy()
        if not text_to_display:
            return

        self.new_window = tk.Toplevel(self)
        self.new_window.title("Dry Run")
        self.new_window.geometry("1000x600")

        fixed_font = font.Font(family="TkFixedFont")
        self.new_window.text = tk.Text(self.new_window, font="TkFixedFont", wrap=tk.NONE, 
                       bg="black", fg="white")
        self.new_window.text.insert(index=tk.END, chars=text_to_display)

        self.new_window.text.pack(padx=5, pady=5, expand=True, fill='both')

class StackRankSorter():
    def __init__(self, config):
        self.organization = config['organization']
        self.project = config['project']
        self.team = config['team']
        pat = config['pat']
        self.encoded_pat = base64.b64encode(f":{pat}".encode()).decode()
        self.priority_field = config['field_priority']
        self.stackrank_field= config['field_stackrank']
        self.result_text = "" # to give feedback to user
        self.result_num_epics = None
        self.result_num_features = None
        self.result_dryRun = ""

    def sort_backlog(self, iteration_path, dryRun=False):
        self.result_text = ""
        self.result_num_epics = 0
        self.result_num_features = 0
        self.result_dryRun = ""

        # Get hierarchy as 'family tree' (includes grandparent's stack rank)
        work_item_ancestry_table = self.get_work_item_ancestrytable(iteration_path)
        if work_item_ancestry_table is None:
            self.result_text = "Nothing to sort: Iteration contains no work items."
        else:
            sort_work_item_table(work_item_ancestry_table)

            # DryRun: Pretty-print results instead of applying order
            if dryRun:
                self.result_dryRun = StackRankSorter.pretty_print_table(work_item_ancestry_table)

            else:
                # Update Stack Rank to match new order
                work_item_ids_ordered = [item.item_id for item in work_item_ancestry_table]
                self.update_stack_rank(work_item_ids_ordered)

                self.result_text = "Backlog items reordered successfully."

        # Gather number of Epics and Features in Iteration
        num_epics_features = StackRankSorter.get_num_epics_features(work_item_ancestry_table)
        self.result_num_epics = num_epics_features[0]
        self.result_num_features = num_epics_features[1]

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
        if response.status_code != 200:
            self.result_text = f"Connection problem - returned {response.status_code} ({response.reason})" 
            return None

        response_json = response.json()
        if response_json['count'] == 0:
            self.result_text = "No iterations found"
            return None

        if not ('value' in response_json):
            print("Could not read value from response... ")
            print(json.dumps(response_json, indent=2))
            return None

        return [item["path"] for item in response_json['value']]

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
        #
        # NOTE: we avoid having to explcitly specifying "Requirement" or "User Story" or any custom work items by
        #       working via elimination instead.
        #
        query_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/wiql?api-version=7.0"
        query = {
            "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.IterationPath] = '{iteration_path}' 
                AND [System.WorkItemType] != 'Task' 
                AND [System.WorkItemType] != 'Feature'
                AND [System.WorkItemType] != 'Epic'
            """
        }
        response = requests.post(query_url, json=query, headers=headers_query)
        if response.status_code != 200:
            return None
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
    def get_num_epics_features(work_item_ancestry_table):
        if work_item_ancestry_table is None:
            return [0, 0]
        
        epics = [item.grandparent for item in work_item_ancestry_table]
        features = [item.parent for item in work_item_ancestry_table]
        
        # Remove 'None' entries 
        epics = [x for x in epics if x is not None]
        features = [x for x in features if x is not None]

        return [len(set(epics)), len(set(features))]

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
            out += "\t" + f"{item.item_type[:15]:<15}"
            out += "\t" + f"{item.item_title[:65]:<65}"

            if item.grandparent_title is not None: 
                out += "\t"
                
                previous_epic = ""
                if i > 0:
                    previous_epic = work_item_ancestry_table[i-1].grandparent_title
                next_epic = ""
                if i < len(work_item_ancestry_table)-1:
                    next_epic = work_item_ancestry_table[i+1].grandparent_title
                
                if item.grandparent_title != previous_epic:
                    out += "┌ " 
                elif item.grandparent_title != next_epic:
                    out += "└ " 
                else:
                    out += "│ "
                
                out += f"{item.grandparent_title[:65]:<65}"

            out += "\n"
            
        return out

def check_config(config):
    class ErrorBox(tk.Tk):
        def __init__(self):
            super().__init__()

        def showError(self, title, msg):
            tk.messagebox.showerror(title, msg)
            self.update()

    error_msgs = ""
    if not config['organization']:
        error_msgs += "'organization', "
    if not config['project']:
        error_msgs += "'project', "  
    if not config['team']:
        error_msgs += "'team', "
    if not config['pat']:
        error_msgs += "'pat', "
    if not config['field_priority']:
        error_msgs += "'field_priority', "
    if not config['field_stackrank']:
        error_msgs += "'field_stackrank', "

    if error_msgs: 
        error_msgs = error_msgs.removesuffix(", ")
        errorBox = ErrorBox()
        errorBox.showError("Config Error", f"The values [{error_msgs}] have not been specified in the config file!")
        errorBox.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()