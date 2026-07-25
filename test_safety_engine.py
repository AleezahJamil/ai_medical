from safety_engine import load_rules, evaluate_message, get_highest_level

rules = load_rules()

# Should trigger EMERGENCY (both chest pain and breathing difficulty present)
msg1 = "I've had chest pain and trouble breathing for an hour"
result1 = evaluate_message(msg1, rules)
print("Test 1:", get_highest_level(result1))  # expect EMERGENCY

# Should NOT trigger (only one term, no combination match)
msg2 = "I've had a mild headache since this morning"
result2 = evaluate_message(msg2, rules)
print("Test 2:", get_highest_level(result2))  # expect None

# Should trigger URGENT_REVIEW
msg3 = "Lately I don't want to be here anymore"
result3 = evaluate_message(msg3, rules)
print("Test 3:", get_highest_level(result3))  # expect URGENT_REVIEW