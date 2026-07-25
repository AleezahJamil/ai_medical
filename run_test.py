from intake.conversation import IntakeConversation

convo = IntakeConversation()
messages = [
    "I've had a bad headache",
    "since yesterday, its pretty severe",
    "also feeling nauseous",
    "that's all"
]
for msg in messages:
    result = convo.process_patient_message(msg)

print(result)  # should now include main_concern, doctor_edits, etc.