#!/usr/bin/python3
"""
Python 3.x GUI App to allow to sort the Azure Sprint Backlog based on some criteria
"""

import sys # for sys.exit
import os
import argparse
import yaml
import shutil

import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import messagebox

from sort_sprint_backlog import StackRankSorter
import app_cfg

def main():
    parser = argparse.ArgumentParser(prog=None)
    parser.add_argument('--config', help='Configuration file that contains credentials and paths to access Azure Boards')
    parser.add_argument('--dryrun', action='store_true', help='Prints resulting order only, without making any modifications')
    args = parser.parse_args()

    if not args.config:
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the PyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app 
            # path into variable _MEIPASS'.
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        print("No config file specified, trying default [config.yml]")
        print("(Application path is ", application_path, " looking for config file in directory ", app_cfg.get_user_config_path())
        
        user_config = app_cfg.get_user_config_path()
        if not user_config.exists():
            shutil.copy(f"{application_path}/config.yml", user_config)
        
        args.config = user_config
    else:
        if not os.path.exists(args.config):
            print("Could not read specified config file")
            sys.exit(-1)

    if args.dryrun:
        print("--dryrun specified!")

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    # DEBUG
    # args.dryrun = True

    # Start GUI
    iteration_selector = IterationSelectorGui(config, args.dryrun)

class IterationSelectorGui(tk.Tk):
    def __init__(self, config, cmdLineDryRun):
        super().__init__()
        self.title("Choose Iteration Backlog to sort")

        self.new_window = None
        self.dryRun = tk.IntVar()
        self.dryRun.set(cmdLineDryRun)
        self.feedback = tk.Label(self, text="")

        # macOS application menu
        menubar = tk.Menu(self)
        app_menu = tk.Menu(menubar, name="apple")  # <-- important!
        app_menu.add_command(label="Configuration...", command=lambda: app_cfg.open_config_window(self))
        menubar.add_cascade(menu=app_menu)
        self.config(menu=menubar)

        # use a frame for the two labels
        frame = tk.Frame(self)
        frame.pack()
        self.labelNumEpics =    tk.Label(frame, text="", font=('TkDefaultFont', 14), fg="orange")
        self.labelNumFeatures = tk.Label(frame, text="", font=('TkDefaultFont', 14), fg="purple")
        self.labelNumEpics.grid(row=0, column=0, padx=15)
        self.labelNumFeatures.grid(row=0, column=1, padx=15)

        self.dropdown = ttk.Combobox(self, text='Iteration')
        self.dropdown.bind('<<ComboboxSelected>>', self.select_dropdown)
        self.dropdown.pack(padx=5, pady=5, fill="x")

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

        self.rebuild_dropdown(config)

        self.tk.mainloop()

    def rebuild_dropdown(self, config):
        self.feedback.config(text="")
        self.labelNumEpics.config(text="")
        self.labelNumFeatures.config(text="")
        
        self.stackrank_sorter = StackRankSorter(config)

        # Check if config is complete and valid
        config_valid = True
        error_msgs = app_cfg.check_config(config)
        if error_msgs:
            config_valid = False
            tk.messagebox.showerror("Config Error", f"The values [{error_msgs}] have not been specified in the config file. Open the config window and add them...")

        iteration_paths = None
        if config_valid:
            # Configure DropDown: Get Iterations and 'Current iteration' (depends on date)
            self.iteration_prefix = f"{self.stackrank_sorter.project}\\"
            iteration_paths = self.stackrank_sorter.get_iterations()
        if iteration_paths is None:
            self.feedback.config(text=self.stackrank_sorter.result_text)
            self.feedback.update()
            iteration_paths = []
            current_iteration = ""
        else:
            iteration_paths = [item.removeprefix(self.iteration_prefix) for item in iteration_paths]
            iterations = self.stackrank_sorter.get_iterations(getCurrentIterationOnly=True)
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
        
        self.dropdown["values"] = iteration_paths
        self.dropdown.set(current_iteration) 

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

if __name__ == "__main__":
    main()