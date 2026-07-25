from checklist import IntakeChecklist

checklist = IntakeChecklist()

headache = checklist.add_symptom("headache")
headache.update("duration", "3 days")
headache.update("severity_reported", "moderate")

nausea = checklist.add_symptom("nausea")
nausea.update("duration", "1 day")
# deliberately leave severity unset on nausea

print("Missing fields for nausea:", nausea.missing_required_fields())
print("Is complete overall:", checklist.is_sufficiently_complete())  # expect False

nausea.update("severity_reported", "mild")
print("Is complete overall now:", checklist.is_sufficiently_complete())  # expect True

# test duplicate handling
same_headache = checklist.add_symptom("Headache")  # different casing
print("Same object?", same_headache is headache)  # expect True

print(checklist.to_dict())