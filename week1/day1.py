company = "Bright Smile Dental"
city = "Austin"
employees = 12

print(f"Company: {company}")
print(f"City: {city}")
print(f"Employees: {employees}")

def describe_lead(name, city, employees):
    return f"{name} is in {city} and has {employees} employees."

print(describe_lead('Bright Smile Dental', 'Austin', 12))
print(describe_lead('Comibitore textiles', 'Tamil Nadu', 30))

def is_good_lead(employees):
    if employees > 5  and employees < 20:
        return True
    return False

print(is_good_lead(12))


leads = ["Coimbatore Textiles", "Kovai Pumps", "Peelamedu Hardware"]

for lead in leads:
    print("Contacting:", lead)

def score_lead(employees, has_website):
    if is_good_lead(employees) and has_website:
        return 10
    elif is_good_lead(employees) or has_website:
        return 5
    else:
        return 0


print(score_lead(12, True))
print(score_lead(12, False))
print(score_lead(100, True))
print(score_lead(100, False))