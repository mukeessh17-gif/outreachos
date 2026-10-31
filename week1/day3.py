# Day 3: Files, JSON, Try/Except, Virtual Environments
# OutreachOS - AI sales outreach tool
# Run this file from inside the week1/ folder.

# ==================================================================
# 1. What is a virtual environment?
# ==================================================================
# A virtual environment is a folder that contains its own copy of Python
# and its own installed packages. Each project gets its own environment,
# so libraries for one project cannot conflict with another project.
# It also lets you share a requirements.txt file so anyone can install
# the exact same packages you used.
# To create and use one:
#   python -m venv .venv          # create the environment folder
#   .venv\Scripts\Activate.ps1    # activate it in PowerShell
#   pip freeze > requirements.txt # save the installed packages

import json
import os

# ==================================================================
# 4. load_leads(path) - returns an empty list if the file is missing
# ==================================================================
def load_leads(path):
    # Try to open the file and read its JSON contents.
    try:
        with open(path, "r") as file:
            return json.load(file)
    # FileNotFoundError happens when the file does not exist.
    except FileNotFoundError:
        # Return an empty list so the rest of the program can keep running.
        return []

# ==================================================================
# 5. save_leads(path, leads) - writes a list of leads to a JSON file
# ==================================================================
def save_leads(path, leads):
    # Open the file for writing and save the list as JSON.
    with open(path, "w") as file:
        json.dump(leads, file, indent=2)
    print("Saved", len(leads), "leads to", path)

# ==================================================================
# 6. TODO: add_lead(path, new_lead)
# ==================================================================
# TODO: Write add_lead(path, new_lead) here.
# It should:
#   - call load_leads(path) to get the current list of leads
#   - append new_lead to that list
#   - call save_leads(path, leads) to save the updated list
#   - print how many leads exist now
# def add_lead(path, new_lead):
#     ...

# ==================================================================
# Only run the demo exercises when this file is run directly.
# When another file (like outreach_cli.py) imports load_leads / save_leads,
# only the function definitions above are loaded - no files are written.
# ==================================================================
if __name__ == "__main__":
    # ==================================================================
    # 2. Write the Day 2 leads list to a JSON file
    # ==================================================================
    # A list of lead dictionaries (the same list from Day 2).
    # Each dictionary holds information about one possible customer.
    leads = [
        {"name": "Kovai Textiles", "employees": 15, "has_website": True},
        {"name": "Peelamedu Hardware", "employees": 30, "has_website": False},
        {"name": "RS Puram Stores", "employees": 8, "has_website": True},
        {"name": "Ganapathy Motors", "employees": 50, "has_website": False},
    ]

    # json.dump() writes Python data into a file in JSON format.
    # "w" means open the file for writing.
    # indent=2 makes the file easy for humans to read.
    with open("leads.json", "w") as file:
        json.dump(leads, file, indent=2)
    print("Wrote leads to leads.json")

    # ==================================================================
    # 3. Read leads.json back and print how many leads are in it
    # ==================================================================
    # "r" means open the file for reading.
    # json.load() reads JSON from the file and turns it back into Python data.
    with open("leads.json", "r") as file:
        leads_again = json.load(file)
    # len() counts how many items are in the list.
    print("Number of leads:", len(leads_again))

    # Demo: try loading a file that does not exist.
    missing_leads = load_leads("does_not_exist.json")
    print("Leads from missing file:", missing_leads)

    # ==================================================================
    # 7. Corrupted JSON demo - catch json.JSONDecodeError
    # ==================================================================
    # Write invalid text into a file so we can see what happens.
    with open("broken.json", "w") as file:
        file.write("{ this is not valid JSON }")

    try:
        # Try to read the broken file as JSON.
        with open("broken.json", "r") as file:
            json.load(file)
    # json.JSONDecodeError happens when the text is not valid JSON.
    except json.JSONDecodeError:
        # Print a friendly message instead of letting the program crash.
        print("Oops! broken.json is not valid JSON. Please check the file.")

    # Remove the broken file so it does not stay on your computer.
    os.remove("broken.json")

    print("Day 3 exercises complete.")