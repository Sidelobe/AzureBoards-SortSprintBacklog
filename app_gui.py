#!/usr/bin/python3
"""
Python 3.x GUI App to allow to sort the Azure Sprint Backlog based on some criteria
"""

import sys # for sys.exit
import os
import argparse
import shutil
from pathlib import Path
import yaml

import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import messagebox

from sort_sprint_backlog import StackRankSorter

APP_NAME = "Azure Backlog Sorter"

def get_user_config_path():
    base = Path.home() / "Library" / "Application Support" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.yml"

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
        print("(Application path is ", application_path, " looking for config file in directory ", get_user_config_path())

        user_config = get_user_config_path()
        if not user_config.exists():
            shutil.copy(f"{application_path}/config.yml", user_config)

        args.config = user_config

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