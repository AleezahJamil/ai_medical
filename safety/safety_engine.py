import os
import json

def load_rules(filepath=None):
    if filepath is None:
        # build a path relative to THIS file's location, not the caller's location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(current_dir, "rules.json")

    with open(filepath, "r") as file:
        rules = json.load(file)
    return rules
def check_pattern_group(message,terms):
    message=message.lower()
    for term in terms:
        if term.lower() in message:
            return True

    return False
#Return True if any term in `terms` appears in `message`
def evaluate_rule(message,rule):
#Check a single rule against the message.
    # Return True if the rule is triggered, False otherwise.
    # Hint: for each pattern group in rule['pattern_groups'], check if it matches
    # (using check_pattern_group), then compare the count of matched groups
    # against rule['min_groups_matched'].
    matched_groups=0
    for group_name,terms in rule["pattern_groups"].items():
        if check_pattern_group(message, terms):#for key, value in pattern_groups.items():
            matched_groups += 1
    if matched_groups >= rule["min_groups_matched"]:
        return True
    return False
def evaluate_message(message, rules):
    # Run all rules against a message.
    # Return a list of triggered rules (or empty list if none).
    triggered_rules = [] # 1. Create an empty list for rules that match

    for rule in rules:# 2. Loop through every rule
        if evaluate_rule(message, rule): # 3. Ask evaluate_rule if this rule matches
            triggered_rules.append(rule) # 4. Add the matching rule to the list
    

    return triggered_rules
def get_highest_level(triggered_rules):
    #Given triggered rules, return the highest priority level.
    # EMERGENCY > URGENT_REVIEW > NOTE
    priority = {
        "NOTE": 1,
        "URGENT_REVIEW": 2,
        "EMERGENCY": 3,
    }
    highest_level = None

    for triggered in triggered_rules:
        current_level = triggered["level"]
        if highest_level is None:
            highest_level = current_level
        elif priority[current_level] > priority[highest_level]:
            highest_level = current_level

    return highest_level