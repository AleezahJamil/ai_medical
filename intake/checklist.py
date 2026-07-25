class SymptomChecklist:
    """
    Tracks collected information for a single symptom during intake.
    """

    def __init__(self, name):
        self.name = name
        self.duration = None
        self.severity_reported = None
        self.severity_inferred = None
        self.severity_inference_evidence = None
        self.location = None
        self.onset_description = None

    def update(self, field, value):
        if hasattr(self, field):
            setattr(self, field, value)
        else:
            print(f"Warning: '{field}' is not a valid field for SymptomChecklist")

    def missing_required_fields(self):
        missing = []
        if self.duration is None:
            missing.append("duration")
        if self.severity_reported is None and self.severity_inferred is None:
            missing.append("severity")
        return missing

    def to_dict(self):
        return {
            "name": self.name,
            "duration": self.duration,
            "severity_reported": self.severity_reported,
            "severity_inferred": self.severity_inferred,
            "severity_inference_evidence": self.severity_inference_evidence,
            "location": self.location,
            "onset_description": self.onset_description,
        }


class IntakeChecklist:
    """
    Tracks all symptoms collected during one intake conversation.
    """

    def __init__(self):
        self.symptoms = []

    def add_symptom(self, name):
        existing = self.get_symptom(name)
        if existing:
            return existing
        new_symptom = SymptomChecklist(name)
        self.symptoms.append(new_symptom)
        return new_symptom

    def get_symptom(self, name):
        for symptom in self.symptoms:
            if symptom.name.lower() == name.lower():
                return symptom
        return None

    def is_sufficiently_complete(self):
        if not self.symptoms:
            return False
        for symptom in self.symptoms:
            if symptom.missing_required_fields():
                return False
        return True

    def to_dict(self):
        return [symptom.to_dict() for symptom in self.symptoms]