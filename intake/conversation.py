import json
import os
from safety.safety_engine import load_rules, evaluate_message, get_highest_level
from groq import Groq
from dotenv import load_dotenv
from intake.checklist import IntakeChecklist
from intake.summary_generator import build_clinical_summary

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MAX_TURNS = 12


class IntakeConversation:
    def __init__(self):
        self.checklist = IntakeChecklist()
        self.safety_rules = load_rules()
        self.turn_count = 0
        self.history = []
        self.emergency_triggered = False
        self.emergency_level = None
        self.ended = False

    def process_patient_message(self, message):
        self.history.append({"role": "patient", "message": message})
        self.turn_count += 1

        triggered = evaluate_message(message, self.safety_rules)
        level = get_highest_level(triggered)

        if level == "EMERGENCY":
            self.emergency_triggered = True
            self.emergency_level = level
            self.ended = True
            return {
                "status": "emergency",
                "message": (
                    "This may be a medical emergency. Please contact emergency "
                    "services or go to your nearest ER immediately."
                ),
                "triggered_rules": [r["rule_id"] for r in triggered],
            }

        if level == "URGENT_REVIEW":
            self.emergency_level = level

        extracted = self._extract_info(message)
        self._apply_extraction(extracted)

        if self._should_end_conversation(message):
            self.ended = True
            summary = self.generate_summary()
            return {"status": "complete", "summary": summary}

        if self.turn_count == 1 and self.history[0].get("message", "").strip().lower() in {"hi", "hello", "hey"}:
            next_question = "Hello. I'm glad you reached out. Take your time—what would you like to talk about today?"
        else:
            next_question = self._generate_next_question()
        self.history.append({"role": "ai", "message": next_question})

        return {"status": "in_progress", "message": next_question}

    def _extract_info(self, message):
        prompt = f"""
You are helping with a mental-health intake conversation. Extract only the
patient-reported concerns, emotions, experiences, and context that are
explicitly stated or clearly implied. Do not invent facts or diagnoses.

Current checklist state: {json.dumps(self.checklist.to_dict())}

Patient message: "{message}"

Return ONLY valid JSON in this format, nothing else:
{{
  "symptoms": [
    {{
      "name": "...",
      "duration": "... or null",
      "severity_reported": "... or null",
      "severity_inferred": "... or null",
      "severity_inference_evidence": "... or null",
      "location": "... or null",
      "onset_description": "... or null"
    }}
  ]
}}
"""
        response_text = self._call_llm(prompt)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"symptoms": []}

    def _apply_extraction(self, extracted):
        for symptom_data in extracted.get("symptoms", []):
            name = symptom_data.get("name")
            if not name:
                continue
            symptom = self.checklist.add_symptom(name)
            for field, value in symptom_data.items():
                if field != "name" and value is not None:
                    symptom.update(field, value)
            self.last_touched_symptom = name  # NEW — remember the most recent one

    def _should_end_conversation(self, message):
        if self.turn_count >= MAX_TURNS:
            return True
        if self._patient_indicates_done(message):
            return True
        if self.checklist.is_sufficiently_complete() and self.turn_count >= 2:
            return self._asked_final_question()
        return False

    def _patient_indicates_done(self, message):
        done_phrases = ["that's all", "nothing else", "no that's it", "that is all"]
        return any(phrase in message.lower() for phrase in done_phrases)

    def _asked_final_question(self):
        return any(
            "anything else" in turn["message"].lower()
            for turn in self.history
            if turn["role"] == "ai"
        )

    def _generate_next_question(self):
        if self.checklist.is_sufficiently_complete():
            return "Is there anything else about this concern that you think is important?"

        last_symptom = getattr(self, "last_touched_symptom", None) or "the patient's most recent concern"
        history_text = "\n".join(
            f"{turn['role']}: {turn['message']}" for turn in self.history[-6:]
        )

        prompt = f"""
You are conducting a calm, empathetic, professional mental-health intake
conversation. Speak like a supportive therapist, not a checklist.

Conversation so far:
{history_text}

The most recent concern mentioned by the patient was: {last_symptom}

Guidelines:
- Start with empathy and acknowledge what the patient shared.
- Ask one natural follow-up question at a time.
- Explore the concern conversationally.
- When relevant, gently understand duration, progression, impact on daily life,
  sleep, studies/work, relationships, or functioning.
- Ask about background and coping strategies naturally when relevant.
- Do not repeat questions already answered.
- Do not diagnose or invent facts.
- Return only the next question text, nothing else.
"""
        return self._call_llm(prompt)

    def _call_llm(self, prompt):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def generate_summary(self):
        return build_clinical_summary(
            checklist_data=self.checklist.to_dict(),
            safety_flag_level=self.emergency_level,
        )