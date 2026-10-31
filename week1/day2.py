# Day 2: Lists and Dictionaries
# OutreachOS - AI sales outreach tool

# Exercise 1
# A list stores many items in one variable, kept in order.
coimbatore_businesses = ["Kovai Textiles", "Peelamedu Hardware", "RS Puram Stores", "Ganapathy Motors", "Sowripalayam Traders"]

# [0] gets the first item in the list.
print("First business:", coimbatore_businesses[0])
# [-1] gets the last item in the list.
print("Last business:", coimbatore_businesses[-1])

# Exercise 2
# len() counts how many items are in the list.
print("Number of businesses:", len(coimbatore_businesses))

# Exercise 3
# .append() adds one new item to the end of the list.
coimbatore_businesses.append("Race Road Autos")
# Print the whole list to see all 6 businesses now.
print("All businesses:", coimbatore_businesses)

# Exercise 4
# The for loop goes through each business name one at a time.
for business in coimbatore_businesses:
    # Print a message for the current business.
    print("Contacting:", business)

# Exercise 5
# A dictionary stores information as key: value pairs.
lead = {
    "name": "Kovai Textiles",
    "city": "Coimbatore",
    "employees": 15,
    "has_website": True,
}

# f-strings let us put variables inside a string using curly braces.
print(f"Name: {lead['name']}")
print(f"City: {lead['city']}")
print(f"Employees: {lead['employees']}")
print(f"Has website: {lead['has_website']}")

# Exercise 6
# Change the employees value to a new number.
lead["employees"] = 18
# Add a new key called email with an email address as its value.
lead["email"] = "info@kovaitextiles.com"
# Print the whole dictionary to see the changes.
print("Updated lead:", lead)

# Exercise 7
# A list of dictionaries, where each dictionary is one lead.
leads = [
    {"name": "Kovai Textiles", "employees": 15, "has_website": True},
    {"name": "Peelamedu Hardware", "employees": 30, "has_website": False},
    {"name": "RS Puram Stores", "employees": 8, "has_website": True},
    {"name": "Ganapathy Motors", "employees": 50, "has_website": False},
]

# Exercise 8
# Loop through each lead dictionary in the list.
for lead in leads:
    # Only print the lead if it has a website.
    if lead["has_website"]:
        print("Lead with website:", lead["name"])

# Exercise 9
# is_good_lead returns True when employees are between 5 and 20 (inclusive).
def is_good_lead(employees):
    if employees >= 5 and employees <= 20:
        return True
    return False

# Loop through each lead and print only the good leads.
for lead in leads:
    if is_good_lead(lead["employees"]):
        print("Good lead:", lead["name"])

# Exercise 10
# TODO: Write score_lead(employees, has_website) here.
# It should return 10 if the lead is a good size and has a website,
# 5 if only one of those is true, and 0 otherwise.
# Then loop through the leads, print "name: score" for each,
# and print the name of the highest-scoring lead.
# def score_lead(employees, has_website):
#     ...

# --- Deliberate errors (commented out so the program still runs) ---
# IndexError: leads[10] does not exist because the list only has 4 items (indexes 0 to 3).
# print(leads[10])
# KeyError: "phone" is not a key in the lead dictionary, so Python cannot look it up.
# print(lead["phone"])