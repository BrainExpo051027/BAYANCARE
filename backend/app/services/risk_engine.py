"""
Rule-based risk classification with confidence scoring (heuristic engine).
Outputs support triage and documentation; they are not validated diagnostic claims.
"""
from app.models.assessment import RiskLevel


def _rule_based_scoring(symptoms_lc, temperature, duration_days, age, chronic_lc, allergies_lc):
    """Original enhanced rule-based logic, extracted so we can layer ML/hybrid logic on top."""
    risk_score = 0
    reasons = []

    symptoms_text = " ".join(symptoms_lc)
    chronic_text = " ".join(chronic_lc)

    # High-risk flags (safety layer inputs)
    if temperature and temperature >= 39.0:
        risk_score += 3
        reasons.append("High fever")
    if "shortness of breath" in symptoms_lc or "difficulty breathing" in symptoms_lc:
        risk_score += 3
        reasons.append("Shortness of breath")
    if "chest pain" in symptoms_lc:
        risk_score += 3
        reasons.append("Chest pain")
    if (
        "hematuria" in symptoms_text
        or "blood in urine" in symptoms_text
        or "bloody urine" in symptoms_text
        or "urine with blood" in symptoms_text
        or "peeing blood" in symptoms_text
        or "pee blood" in symptoms_text
        or (
            "blood" in symptoms_text
            and (
                "urine" in symptoms_text
                or "pee" in symptoms_text
                or "peeing" in symptoms_text
                or "urinating" in symptoms_text
                or "urination" in symptoms_text
            )
        )
    ):
        risk_score += 3
        reasons.append("Blood in urine")
    if (
        "vomiting blood" in symptoms_text
        or "vomit blood" in symptoms_text
        or "hematemesis" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Vomiting blood")
    if (
        "blood in stool" in symptoms_text
        or "bloody stool" in symptoms_text
        or "rectal bleeding" in symptoms_text
        or "black stool" in symptoms_text
        or "black stools" in symptoms_text
        or "tarry stool" in symptoms_text
        or "tarry stools" in symptoms_text
        or "melena" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Possible gastrointestinal bleeding")
    if (
        "fainting" in symptoms_text
        or "fainted" in symptoms_text
        or "passed out" in symptoms_text
        or "unconscious" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Fainting/Unconscious")
    if (
        "anaphylaxis" in symptoms_text
        or "throat swelling" in symptoms_text
        or "swollen throat" in symptoms_text
        or "tongue swelling" in symptoms_text
        or "swollen tongue" in symptoms_text
        or "swollen lips" in symptoms_text
        or "lip swelling" in symptoms_text
        or "face swelling" in symptoms_text
        or "swollen face" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Possible severe allergic reaction")
    if (
        "stroke" in symptoms_text
        or "facial droop" in symptoms_text
        or "face drooping" in symptoms_text
        or "slurred speech" in symptoms_text
        or "unable to speak" in symptoms_text
        or "difficulty speaking" in symptoms_text
        or "one-sided weakness" in symptoms_text
        or "one sided weakness" in symptoms_text
        or "weakness on one side" in symptoms_text
        or "one-sided numbness" in symptoms_text
        or "one sided numbness" in symptoms_text
        or "numbness on one side" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Possible stroke warning signs")
    if (
        "severe abdominal pain" in symptoms_text
        or "severe stomach pain" in symptoms_text
        or "rigid abdomen" in symptoms_text
        or "hard abdomen" in symptoms_text
        or "appendicitis" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Severe abdominal pain")
    if (
        "dehydration" in symptoms_text
        or "not urinating" in symptoms_text
        or "no urine" in symptoms_text
        or "not peeing" in symptoms_text
        or "unable to urinate" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Severe dehydration / low urine output")
    if (
        "head injury" in symptoms_text
        or "hit head" in symptoms_text
        or "traumatic brain" in symptoms_text
        or "concussion" in symptoms_text
    ):
        risk_score += 3
        reasons.append("Head injury")
    if (
        ("pregnan" in symptoms_text)
        and (
            "vaginal bleeding" in symptoms_text
            or "bleeding" in symptoms_text
            or "spotting" in symptoms_text
        )
    ):
        risk_score += 3
        reasons.append("Pregnancy with bleeding")
    if "confusion" in symptoms_lc or "disorientation" in symptoms_lc:
        risk_score += 3
        reasons.append("Confusion/Disorientation")
    if "severe headache" in symptoms_lc or "headache" in symptoms_lc and (
        "stiff neck" in symptoms_lc or "vomiting" in symptoms_lc
    ):
        risk_score += 3
        reasons.append("Severe headache with red flags")
    if "persistent vomiting" in symptoms_lc or "unable to keep fluids" in symptoms_lc:
        risk_score += 3
        reasons.append("Persistent vomiting/dehydration risk")
    if "rash" in symptoms_lc and ("fever" in symptoms_lc or "stiff neck" in symptoms_lc):
        risk_score += 3
        reasons.append("Fever with rash (possible meningitis)")
    if duration_days and duration_days >= 5:
        risk_score += 2
        reasons.append("Symptoms lasting 5+ days")

    # Symptom cluster detection for specific dangerous conditions
    # Dengue cluster (fever + headache + eye pain + joint/muscle pain)
    if (
        "fever" in symptoms_text
        and ("headache" in symptoms_text or "severe headache" in symptoms_text)
        and (
            "eye pain" in symptoms_text
            or "pain behind eyes" in symptoms_text
            or "retro orbital pain" in symptoms_text
            or "behind eyes" in symptoms_text
        )
        and (
            "joint pain" in symptoms_text
            or "muscle pain" in symptoms_text
            or "body aches" in symptoms_text
            or "back pain" in symptoms_text
        )
    ):
        risk_score += 4
        reasons.append("Possible dengue fever cluster")

    # Silent MI / Atypical heart attack symptoms
    if (
        any(x in symptoms_text for x in ["jaw pain", "jaw ache", "jaw discomfort"])
        or any(x in symptoms_text for x in ["left arm pain", "left arm numb", "arm pain"])
        or any(x in symptoms_text for x in ["shoulder pain", "shoulder ache"])
        or any(x in symptoms_text for x in ["upper back pain", "back pain"])
        or "sweating" in symptoms_text
        or "cold sweat" in symptoms_text
        or "clammy" in symptoms_text
    ) and any(x in symptoms_text for x in ["nausea", "fatigue", "tired", "weakness"]):
        risk_score += 3
        reasons.append("Possible atypical cardiac symptoms")

    # Sepsis indicators
    if (
        "fever" in symptoms_text
        or "chills" in symptoms_text
        or "shivering" in symptoms_text
    ) and (
        any(x in symptoms_text for x in ["rapid heartbeat", "fast heart rate", "heart racing", "palpitations"])
        or any(x in symptoms_text for x in ["rapid breathing", "fast breathing", "shortness of breath", "breathing fast"])
        or "confusion" in symptoms_text
        or "extreme fatigue" in symptoms_text
    ):
        risk_score += 4
        reasons.append("Possible sepsis indicators")

    # Meningitis without stiff neck (photophobia cluster)
    if (
        "fever" in symptoms_text
        and ("headache" in symptoms_text or "severe headache" in symptoms_text)
        and (
            "photophobia" in symptoms_text
            or "sensitivity to light" in symptoms_text
            or "light sensitivity" in symptoms_text
            or "light hurts" in symptoms_text
        )
    ):
        risk_score += 4
        reasons.append("Possible meningitis (photophobia)")

    # Appendicitis early indicators
    if (
        any(x in symptoms_text for x in ["pain near belly button", "belly button pain", "navel pain", "periumbilical pain"])
        or any(x in symptoms_text for x in ["right lower abdominal pain", "right side stomach pain", "rlq pain"])
        or any(x in symptoms_text for x in ["loss of appetite", "not hungry", "decreased appetite"])
        or "rebound tenderness" in symptoms_text
    ) and ("nausea" in symptoms_text or "vomiting" in symptoms_text or "low fever" in symptoms_text or "mild fever" in symptoms_text):
        risk_score += 3
        reasons.append("Possible appendicitis indicators")

    # Pulmonary embolism indicators
    if (
        any(x in symptoms_text for x in ["sudden shortness of breath", "sudden breathlessness"])
        or any(x in symptoms_text for x in ["chest tightness", "chest pressure", "chest discomfort"])
        or any(x in symptoms_text for x in ["coughing blood", "blood in cough", "bloody cough", "hemoptysis"])
        or any(x in symptoms_text for x in ["rapid heartbeat", "fast heart rate", "heart racing", "palpitations"])
        or any(x in symptoms_text for x in ["sudden dizziness", "lightheaded", "about to faint"])
    ):
        risk_score += 4
        reasons.append("Possible pulmonary embolism")

    # DKA (Diabetic Ketoacidosis) - requires diabetes in chronic conditions
    has_diabetes = any(cond in chronic_lc for cond in ["diabetes", "diabetic"])
    if has_diabetes and (
        any(x in symptoms_text for x in ["extreme thirst", "excessive thirst", "very thirsty", "fruity breath", "sweet breath", "acetone breath"])
        or any(x in symptoms_text for x in ["frequent urination", "peeing a lot", "urinating frequently"])
        or ("abdominal pain" in symptoms_text or "stomach pain" in symptoms_text)
        or "confusion" in symptoms_text
    ):
        risk_score += 4
        reasons.append("Possible diabetic ketoacidosis (DKA)")

    # Tuberculosis indicators (persistent cough + weight loss/night sweats)
    if (
        ("cough" in symptoms_text and duration_days and duration_days >= 14)
        or "persistent cough" in symptoms_text
        or "chronic cough" in symptoms_text
    ) and (
        any(x in symptoms_text for x in ["weight loss", "losing weight", "unintentional weight loss"])
        or any(x in symptoms_text for x in ["night sweats", "sweating at night", "drenching sweats"])
    ):
        risk_score += 3
        reasons.append("Possible tuberculosis indicators")

    # Heat stroke / heat exhaustion (important for tropical climate)
    if (
        any(x in symptoms_text for x in ["heat exposure", "overheating", "heat stroke", "heat exhaustion", "heat cramps"])
        or ("high temperature" in symptoms_text and any(x in symptoms_text for x in ["hot weather", "sun exposure", "working outside"]))
    ) and (
        "dizziness" in symptoms_text
        or "confusion" in symptoms_text
        or "dry skin" in symptoms_text
        or "not sweating" in symptoms_text
        or "nausea" in symptoms_text
    ):
        risk_score += 4
        reasons.append("Possible heat-related illness")

    # Posterior stroke / atypical stroke symptoms
    if (
        any(x in symptoms_text for x in ["sudden dizziness", "vertigo", "spinning", "loss of balance", "unsteady", "falling over"])
        or any(x in symptoms_text for x in ["double vision", "blurred vision", "vision changes", "seeing double"])
        or any(x in symptoms_text for x in ["sudden severe headache", "thunderclap headache", "worst headache"])
    ):
        risk_score += 3
        reasons.append("Possible posterior stroke / neurological emergency")

    # Internal bleeding indicators (when no visible blood)
    if (
        any(x in symptoms_text for x in ["severe dizziness", "extreme dizziness", "about to pass out", "lightheaded"])
        or any(x in symptoms_text for x in ["pale skin", "pale", "clamminess", "cold clammy skin"])
        or any(x in symptoms_text for x in ["abdominal swelling", "belly swelling", "swollen abdomen", "distended abdomen"])
        or any(x in symptoms_text for x in ["weakness", "extreme fatigue", "very tired"])
    ) and ("fainting" in symptoms_text or "confusion" in symptoms_text or "rapid heartbeat" in symptoms_text):
        risk_score += 4
        reasons.append("Possible internal bleeding / shock")

    # Additional individual high-risk symptoms
    if (
        "rapid heartbeat" in symptoms_text
        or "fast heart rate" in symptoms_text
        or "heart racing" in symptoms_text
        or "palpitations" in symptoms_text
        or "irregular heartbeat" in symptoms_text
    ):
        risk_score += 2
        reasons.append("Cardiac rhythm concern")

    if (
        "chills" in symptoms_text
        or "shivering" in symptoms_text
        or "rigors" in symptoms_text
    ):
        risk_score += 2
        reasons.append("Chills (possible serious infection)")

    if (
        "night sweats" in symptoms_text
        or "sweating at night" in symptoms_text
        or "drenching sweats" in symptoms_text
    ):
        risk_score += 2
        reasons.append("Night sweats")

    if (
        "weight loss" in symptoms_text
        or "losing weight" in symptoms_text
        and ("unintentional" in symptoms_text or duration_days and duration_days >= 30)
    ):
        risk_score += 2
        reasons.append("Unintentional weight loss")

    if (
        "coughing blood" in symptoms_text
        or "blood in cough" in symptoms_text
        or "bloody cough" in symptoms_text
        or "hemoptysis" in symptoms_text
    ):
        risk_score += 4
        reasons.append("Coughing blood (hemoptysis)")

    # Moderate-risk flags
    if "cough" in symptoms_lc and duration_days and duration_days >= 2:
        risk_score += 1
        reasons.append("Persistent cough")
    if "sore throat" in symptoms_lc and ("fever" in symptoms_lc or "swollen glands" in symptoms_lc):
        risk_score += 1
        reasons.append("Sore throat with fever")
    if "diarrhea" in symptoms_lc or "vomiting" in symptoms_lc:
        risk_score += 1
        reasons.append("Gastrointestinal symptoms")
    if "body aches" in symptoms_lc or "muscle pain" in symptoms_lc:
        risk_score += 1
        reasons.append("Body aches")
    if "fatigue" in symptoms_lc or "weakness" in symptoms_lc:
        risk_score += 1
        reasons.append("Fatigue/weakness")
    if "loss of taste" in symptoms_lc or "loss of smell" in symptoms_lc:
        risk_score += 1
        reasons.append("Loss of taste/smell")
    if duration_days and duration_days >= 3:
        risk_score += 1
        reasons.append("Symptoms lasting 3+ days")

    # Age-based risk
    if age:
        if age >= 65:
            risk_score += 2
            reasons.append("Elderly patient (65+)")
        elif age >= 60:
            risk_score += 1
            reasons.append("Older adult (60-64)")
        elif age <= 5:
            risk_score += 1
            reasons.append("Young child (≤5)")

    # Chronic condition risk
    if any(cond in chronic_lc for cond in ["asthma", "copd", "chronic lung"]):
        risk_score += 2
        reasons.append("Chronic lung disease")
    if any(cond in chronic_lc for cond in ["diabetes", "diabetic"]):
        risk_score += 2
        reasons.append("Diabetes")
    if any(cond in chronic_lc for cond in ["heart disease", "heart failure", "cardiac"]):
        risk_score += 2
        reasons.append("Heart disease")
    if any(cond in chronic_lc for cond in ["kidney disease", "renal"]):
        risk_score += 2
        reasons.append("Kidney disease")
    if any(
        cond in chronic_lc
        for cond in ["immunocompromised", "immunosuppressed", "hiv", "aids", "cancer", "chemotherapy",
                     "leukemia", "lymphoma", "tumor", "radiation therapy", "radiotherapy",
                     "organ transplant", "transplant", "lupus", "autoimmune"]
    ):
        risk_score += 3
        reasons.append("Immunocompromised")

    immunocompromised = any(
        key in " ".join(chronic_lc)
        for key in ["immunocompromised", "immunosuppressed", "hiv", "aids", "cancer", "chemotherapy",
                    "leukemia", "lymphoma", "tumor", "radiation therapy", "radiotherapy",
                    "organ transplant", "transplant", "lupus", "autoimmune"]
    )
    # Immunocompromised patients with any symptom always push to HIGH
    if immunocompromised and (symptoms_lc or temperature is not None):
        risk_score += 5  # Guarantees >= 7 threshold for HIGH
        reasons.append("Immunocompromised patient — automatic escalation")
    if "hypertension" in chronic_lc or "high blood pressure" in chronic_lc:
        risk_score += 1
        reasons.append("Hypertension")

    has_medication_allergy = any(
        allergy in allergies_lc for allergy in ["penicillin", "aspirin", "nsaid", "ibuprofen", "paracetamol"]
    )

    return risk_score, reasons, has_medication_allergy


def _infer_condition(symptoms_lc, duration_days=None, chronic_lc=None):
    """Very simple condition label based on common symptom clusters."""
    symptoms_text = " ".join(symptoms_lc)
    chronic_lc = chronic_lc or []
    chronic_text = " ".join(chronic_lc)

    # --- Immunocompromised / chronic critical conditions first ---
    immunocompromised_conditions = [
        ("cancer", "Active cancer – requires oncologist/specialist evaluation"),
        ("leukemia", "Leukemia – requires specialist evaluation"),
        ("lymphoma", "Lymphoma – requires specialist evaluation"),
        ("chemotherapy", "Patient on chemotherapy – immediate medical review required"),
        ("radiotherapy", "Patient on radiation therapy – immediate medical review required"),
        ("radiation therapy", "Patient on radiation therapy – immediate medical review required"),
        ("hiv", "HIV/AIDS – requires specialist evaluation"),
        ("aids", "HIV/AIDS – requires specialist evaluation"),
        ("immunocompromised", "Immunocompromised patient – requires immediate medical evaluation"),
        ("immunosuppressed", "Immunosuppressed patient – requires immediate medical evaluation"),
        ("organ transplant", "Organ transplant patient – requires immediate medical evaluation"),
        ("transplant", "Transplant patient – requires immediate medical evaluation"),
        ("lupus", "Autoimmune disease (Lupus) – requires specialist evaluation"),
        ("autoimmune", "Autoimmune disease – requires specialist evaluation"),
    ]
    for key, label in immunocompromised_conditions:
        if key in chronic_text:
            return label

    # Critical symptom conditions
    if "stroke" in symptoms_text:
        return "Possible stroke - EMERGENCY"
    if (
        "facial droop" in symptoms_text
        or "face drooping" in symptoms_text
        or "slurred speech" in symptoms_text
        or "unable to speak" in symptoms_text
        or "difficulty speaking" in symptoms_text
        or "one-sided weakness" in symptoms_text
        or "one sided weakness" in symptoms_text
        or "weakness on one side" in symptoms_text
        or "one-sided numbness" in symptoms_text
        or "one sided numbness" in symptoms_text
        or "numbness on one side" in symptoms_text
    ):
        return "Possible stroke warning signs – EMERGENCY"
    if "heart attack" in symptoms_text or "chest pain" in symptoms_text:
        return "Possible cardiac event - EMERGENCY"
    if "severe bleeding" in symptoms_text:
        return "Severe bleeding - EMERGENCY"
    if "seizure" in symptoms_text:
        return "Seizure activity - requires urgent evaluation"
    if "suicidal" in symptoms_text:
        return "Mental health crisis - immediate intervention needed"
    
    # Other conditions
    if (
        "hematuria" in symptoms_text
        or "blood in urine" in symptoms_text
        or "bloody urine" in symptoms_text
        or "urine with blood" in symptoms_text
        or "peeing blood" in symptoms_text
        or "pee blood" in symptoms_text
        or (
            "blood" in symptoms_text
            and (
                "urine" in symptoms_text
                or "pee" in symptoms_text
                or "peeing" in symptoms_text
                or "urinating" in symptoms_text
                or "urination" in symptoms_text
            )
        )
    ):
        return "Possible urinary tract/kidney issue (blood in urine) – urgent evaluation"
    if "vomiting blood" in symptoms_text or "vomit blood" in symptoms_text or "hematemesis" in symptoms_text:
        return "Possible gastrointestinal bleeding (vomiting blood) – EMERGENCY"
    if (
        "blood in stool" in symptoms_text
        or "bloody stool" in symptoms_text
        or "rectal bleeding" in symptoms_text
        or "black stool" in symptoms_text
        or "black stools" in symptoms_text
        or "tarry stool" in symptoms_text
        or "tarry stools" in symptoms_text
        or "melena" in symptoms_text
    ):
        return "Possible gastrointestinal bleeding (blood/black stool) – urgent evaluation"
    if "anaphylaxis" in symptoms_text or "throat swelling" in symptoms_text or "tongue swelling" in symptoms_text:
        return "Possible severe allergic reaction (airway swelling) – EMERGENCY"
    if (
        "severe abdominal pain" in symptoms_text
        or "severe stomach pain" in symptoms_text
        or "rigid abdomen" in symptoms_text
        or "hard abdomen" in symptoms_text
        or "appendicitis" in symptoms_text
    ):
        return "Possible acute abdomen (severe abdominal pain) – urgent evaluation"
    if (
        "dehydration" in symptoms_text
        or "not urinating" in symptoms_text
        or "no urine" in symptoms_text
        or "not peeing" in symptoms_text
        or "unable to urinate" in symptoms_text
    ):
        return "Possible severe dehydration / low urine output – urgent evaluation"
    if (
        "head injury" in symptoms_text
        or "hit head" in symptoms_text
        or "traumatic brain" in symptoms_text
        or "concussion" in symptoms_text
    ):
        return "Possible head injury – urgent evaluation"
    if (
        ("pregnan" in symptoms_text)
        and (
            "vaginal bleeding" in symptoms_text
            or "bleeding" in symptoms_text
            or "spotting" in symptoms_text
        )
    ):
        return "Pregnancy with bleeding – EMERGENCY"

    # Dengue cluster detection
    if (
        "fever" in symptoms_text
        and ("headache" in symptoms_text or "severe headache" in symptoms_text)
        and (
            "eye pain" in symptoms_text
            or "pain behind eyes" in symptoms_text
            or "retro orbital pain" in symptoms_text
            or "behind eyes" in symptoms_text
        )
        and (
            "joint pain" in symptoms_text
            or "muscle pain" in symptoms_text
            or "body aches" in symptoms_text
        )
    ):
        return "Possible dengue fever – urgent evaluation (common in Philippines)"

    # Silent MI / Atypical heart attack
    if (
        any(x in symptoms_text for x in ["jaw pain", "jaw ache", "left arm pain", "arm pain", "shoulder pain", "upper back pain"])
        or "sweating" in symptoms_text
        or "cold sweat" in symptoms_text
    ) and any(x in symptoms_text for x in ["nausea", "fatigue", "tired", "weakness"]):
        return "Possible silent heart attack / atypical cardiac symptoms – EMERGENCY"

    # Sepsis indicators
    if (
        "fever" in symptoms_text
        or "chills" in symptoms_text
        or "shivering" in symptoms_text
    ) and (
        any(x in symptoms_text for x in ["rapid heartbeat", "fast heart rate", "heart racing"])
        or any(x in symptoms_text for x in ["rapid breathing", "fast breathing", "breathing fast"])
        or "confusion" in symptoms_text
    ):
        return "Possible sepsis – EMERGENCY"

    # Meningitis with photophobia
    if (
        "fever" in symptoms_text
        and ("headache" in symptoms_text or "severe headache" in symptoms_text)
        and (
            "photophobia" in symptoms_text
            or "sensitivity to light" in symptoms_text
            or "light sensitivity" in symptoms_text
        )
    ):
        return "Possible meningitis (photophobia) – urgent evaluation"

    # DKA for diabetic patients
    has_diabetes_text = "diabetes" in symptoms_text or "diabetic" in symptoms_text
    if has_diabetes_text and (
        any(x in symptoms_text for x in ["extreme thirst", "excessive thirst", "fruity breath", "sweet breath"])
        or "frequent urination" in symptoms_text
        or "confusion" in symptoms_text
    ):
        return "Possible diabetic ketoacidosis (DKA) – EMERGENCY"

    # Tuberculosis
    if (
        ("cough" in symptoms_text and duration_days is not None and duration_days >= 14)
        or "persistent cough" in symptoms_text
    ) and (
        any(x in symptoms_text for x in ["weight loss", "losing weight"])
        or any(x in symptoms_text for x in ["night sweats", "sweating at night"])
    ):
        return "Possible tuberculosis – requires evaluation and testing"

    # Internal bleeding indicators (check before PE which also matches rapid heartbeat)
    if (
        any(x in symptoms_text for x in ["severe dizziness", "pale skin", "abdominal swelling"])
        and ("fainting" in symptoms_text or "rapid heartbeat" in symptoms_text)
    ):
        return "Possible internal bleeding / shock – EMERGENCY"

    # Pulmonary embolism (requires more specific symptoms than just rapid heartbeat)
    if (
        any(x in symptoms_text for x in ["sudden shortness of breath", "sudden breathlessness"])
        or any(x in symptoms_text for x in ["chest tightness", "chest pressure"])
        or "coughing blood" in symptoms_text
    ) and (
        any(x in symptoms_text for x in ["rapid heartbeat", "fast heart rate", "heart racing"])
        or "sudden dizziness" in symptoms_text
    ):
        return "Possible pulmonary embolism – EMERGENCY"

    # Heat stroke / heat exhaustion
    if (
        any(x in symptoms_text for x in ["heat exposure", "overheating", "heat stroke", "heat exhaustion"])
        and (
            "confusion" in symptoms_text
            or "dry skin" in symptoms_text
            or "not sweating" in symptoms_text
            or "dizziness" in symptoms_text
        )
    ):
        return "Possible heat stroke – EMERGENCY (cool immediately and seek care)"

    # Posterior stroke
    if (
        any(x in symptoms_text for x in ["sudden dizziness", "vertigo", "loss of balance", "double vision", "blurred vision"])
        or "sudden severe headache" in symptoms_text
    ):
        return "Possible posterior stroke / neurological emergency"

    if "shortness of breath" in symptoms_lc or "difficulty breathing" in symptoms_lc:
        return "Possible respiratory/cardiac emergency"
    if "fever" in symptoms_lc and "cough" in symptoms_lc:
        return "Possible respiratory infection"
    if "fever" in symptoms_lc and "rash" in symptoms_lc:
        return "Possible infectious disease with rash"
    if "diarrhea" in symptoms_lc or "vomiting" in symptoms_lc:
        return "Possible gastrointestinal infection"
    if "headache" in symptoms_lc and "stiff neck" in symptoms_lc:
        return "Possible meningitis – urgent evaluation"
    return "Non-specific / mild illness pattern"


def classify_risk(symptoms, temperature, duration_days, age, allergies, chronic_conditions):
    """
    Hybrid-style classifier interface.
    Currently uses an enhanced rule-based core with safety override and
    exposes prediction metadata expected by the modern frontend.

    Returns:
        risk_level (RiskLevel)
        summary (str)
        recommendations (str)
        follow_up_required (bool)
        predicted_condition (str)
        confidence_score (float, 0–1)
    """
    # Normalize inputs
    symptoms_lc = [s.lower() for s in symptoms] if symptoms else []
    chronic_lc = [c.lower() for c in chronic_conditions] if chronic_conditions else []
    allergies_lc = [a.lower() for a in allergies] if allergies else []

    # Rule-based scoring
    risk_score, reasons, has_medication_allergy = _rule_based_scoring(
        symptoms_lc, temperature, duration_days, age, chronic_lc, allergies_lc
    )

    # Safety layer: any clear red-flag symptoms force at least HIGH risk
    safety_flags = {
        "shortness of breath",
        "difficulty breathing",
        "chest pain",
        "confusion",
        "disorientation",
        "persistent vomiting",
        "cancer",
        "severe bleeding",
        "blood in urine",
        "bloody urine",
        "urine with blood",
        "peeing blood",
        "pee blood",
        "hematuria",
        "vomiting blood",
        "vomit blood",
        "hematemesis",
        "blood in stool",
        "bloody stool",
        "rectal bleeding",
        "black stool",
        "black stools",
        "tarry stool",
        "tarry stools",
        "melena",
        "fainting",
        "fainted",
        "passed out",
        "anaphylaxis",
        "throat swelling",
        "swollen throat",
        "tongue swelling",
        "swollen tongue",
        "swollen lips",
        "lip swelling",
        "face swelling",
        "swollen face",
        "unconscious",
        "seizure",
        "stroke",
        "facial droop",
        "face drooping",
        "slurred speech",
        "unable to speak",
        "difficulty speaking",
        "one-sided weakness",
        "one sided weakness",
        "weakness on one side",
        "one-sided numbness",
        "one sided numbness",
        "numbness on one side",
        "heart attack",
        "suicidal",
        "overdose",
        "poisoning",
        "severe burn",
        "severe abdominal pain",
        "severe stomach pain",
        "rigid abdomen",
        "hard abdomen",
        "appendicitis",
        "dehydration",
        "not urinating",
        "no urine",
        "not peeing",
        "unable to urinate",
        "head injury",
        "hit head",
        "traumatic brain",
        "concussion",
        "vaginal bleeding",
        "pregnant bleeding",
        "pregnancy bleeding",
        "pregnant spotting",
        "rapid heartbeat",
        "fast heart rate",
        "heart racing",
        "palpitations",
        "irregular heartbeat",
        "chills",
        "shivering",
        "rigors",
        "night sweats",
        "sweating at night",
        "drenching sweats",
        "coughing blood",
        "blood in cough",
        "bloody cough",
        "hemoptysis",
        "double vision",
        "blurred vision",
        "vision changes",
        "seeing double",
        "loss of balance",
        "sudden dizziness",
        "jaw pain",
        "jaw ache",
        "left arm pain",
        "arm pain",
        "shoulder pain",
        "upper back pain",
        "persistent cough",
        "chronic cough",
        "photophobia",
        "sensitivity to light",
        "light sensitivity",
        "fruity breath",
        "sweet breath",
        "acetone breath",
        "extreme thirst",
        "excessive thirst",
        "very thirsty",
        "frequent urination",
        "paralysis",
        "unable to move",
    }
    joined_symptoms = " ".join(symptoms_lc)
    safety_triggered = any(flag in joined_symptoms for flag in safety_flags)
    safety_triggered = safety_triggered or (
        "blood" in joined_symptoms
        and (
            "urine" in joined_symptoms
            or "pee" in joined_symptoms
            or "peeing" in joined_symptoms
            or "urinating" in joined_symptoms
            or "urination" in joined_symptoms
        )
    )

    chronic_joined = " ".join(chronic_lc)
    immunocompromised = any(
        key in chronic_joined
        for key in ["immunocompromised", "immunosuppressed", "hiv", "aids", "cancer", "chemotherapy",
                    "leukemia", "lymphoma", "tumor", "radiation therapy", "radiotherapy",
                    "organ transplant", "transplant", "lupus", "autoimmune"]
    )
    fever_present = (
        (temperature is not None and temperature >= 38.0)
        or ("fever" in joined_symptoms)
    )
    # Immunocompromised patients (cancer, HIV, chemotherapy, etc.) with ANY reported symptom
    # always require HIGH risk — their weakened immune system makes even mild symptoms dangerous.
    if immunocompromised and symptoms_lc:
        safety_triggered = True
    else:
        safety_triggered = safety_triggered or (immunocompromised and fever_present)

    # Map score to risk level
    if risk_score >= 7 or safety_triggered:
        risk = RiskLevel.HIGH
        follow_up_required = True
        summary = "High risk condition. Immediate medical consultation recommended."
        recommendations = (
            "Seek immediate medical attention at the nearest health facility. "
            "If severe symptoms worsen (e.g., shortness of breath, chest pain, confusion, blood in urine), go to the emergency room."
        )
    elif risk_score >= 4:
        risk = RiskLevel.MODERATE
        follow_up_required = True
        summary = "Moderate risk. Monitor closely and consider consultation if no improvement."
        recommendations = (
            "Rest, hydrate, and monitor symptoms. "
            "If symptoms persist beyond 3 days or worsen, consult a health worker."
        )
    else:
        risk = RiskLevel.LOW
        follow_up_required = False
        summary = "Low risk. Home care is usually sufficient."
        recommendations = (
            "Home care: rest, fluids, and over-the-counter remedies "
            "(avoid known allergies). Monitor for any worsening."
        )

    if has_medication_allergy:
        recommendations += " Avoid medications you are allergic to; consult a pharmacist if unsure."
        summary += " Note: You have reported medication allergies."

    # Very simple confidence score: normalized risk score with floor/ceiling
    # In a real ML model this would come from predict_proba; this keeps the same interface.
    max_score = 10.0
    raw_conf = risk_score / max_score if max_score else 0.0
    confidence_score = max(0.5, min(raw_conf, 0.99))

    predicted_condition = _infer_condition(symptoms_lc, duration_days, chronic_lc)

    return risk, summary, recommendations, follow_up_required, predicted_condition, confidence_score, has_medication_allergy


def get_home_care_plan(risk, symptoms, has_medication_allergy):
    """
    Generate specific home care plan with medication, rest, and exercise guidance
    for LOW and MODERATE risk assessments.
    """
    symptoms_lc = [s.lower() for s in symptoms] if symptoms else []
    
    plan = {
        "risk_level": risk.value if hasattr(risk, 'value') else risk,
        "general_advice": "",
        "medications": [],
        "rest_and_recovery": {},
        "exercise": {},
        "diet_and_hydration": {},
        "when_to_seek_care": "",
        "estimated_recovery_time": ""
    }
    
    # Common OTC medications advice (with allergy warnings)
    safe_meds = []
    if not has_medication_allergy:
        if "fever" in symptoms_lc or "headache" in symptoms_lc or "body aches" in symptoms_lc:
            safe_meds.append({
                "name": "Paracetamol (Acetaminophen)",
                "dosage": "500mg every 4-6 hours as needed",
                "max_daily": "Do not exceed 4,000mg in 24 hours",
                "notes": "Take with food if stomach upset occurs"
            })
        if "cough" in symptoms_lc:
            safe_meds.append({
                "name": "Carbocisteine or guaifenesin (expectorant)",
                "dosage": "As directed on package",
                "notes": "Drink plenty of water to help loosen mucus"
            })
        if "sore throat" in symptoms_lc:
            safe_meds.append({
                "name": "Saline gargle or lozenges",
                "dosage": "Gargle 3-4 times daily or use lozenges as needed",
                "notes": "Warm salt water (1/2 tsp salt in 1 cup warm water)"
            })
        if "diarrhea" in symptoms_lc:
            safe_meds.append({
                "name": "Oral Rehydration Solution (ORS)",
                "dosage": "Drink after each loose stool",
                "notes": "Can use commercial ORS or make at home (1L water + 6 tsp sugar + 1/2 tsp salt)"
            })
        if "nasal congestion" in symptoms_lc or "runny nose" in symptoms_lc:
            safe_meds.append({
                "name": "Saline nasal spray",
                "dosage": "2-3 sprays per nostril, 3-4 times daily",
                "notes": "Safe for all ages, non-medicated"
            })
    else:
        safe_meds.append({
            "warning": "You have reported medication allergies. Consult a pharmacist before taking any medication.",
            "general_advice": "Use non-pharmacological remedies (rest, fluids, humidifier)"
        })
    
    plan["medications"] = safe_meds
    
    # Risk-specific plans
    if risk.value == "LOW" if hasattr(risk, 'value') else risk == "LOW":
        plan["general_advice"] = "Your condition appears mild. Home care should be sufficient for recovery."
        plan["rest_and_recovery"] = {
            "sleep": "7-9 hours per night",
            "activity_level": "Light activity as tolerated",
            "work_school": "Can usually continue with normal activities"
        }
        plan["exercise"] = {
            "allowed": "Light walking, stretching",
            "avoid": "Strenuous exercise until fully recovered",
            "duration": "15-20 minutes light activity if feeling up to it"
        }
        plan["diet_and_hydration"] = {
            "fluids": "8-10 glasses of water daily",
            "foods": "Nutritious, easy-to-digest foods: soup, fruits, vegetables, lean protein",
            "avoid": "Alcohol, excessive caffeine, greasy foods"
        }
        plan["when_to_seek_care"] = "If symptoms worsen, persist beyond 3-5 days, or new symptoms develop"
        plan["estimated_recovery_time"] = "2-3 days for mild conditions"
        
    elif risk.value == "MODERATE" if hasattr(risk, 'value') else risk == "MODERATE":
        plan["general_advice"] = "Your condition requires careful monitoring. Follow this plan closely and watch for any worsening."
        plan["rest_and_recovery"] = {
            "sleep": "8-10 hours per night, take naps as needed",
            "activity_level": "Rest is priority - limit activity to essential tasks only",
            "work_school": "Consider taking 1-2 days off to recover faster"
        }
        plan["exercise"] = {
            "allowed": "Very light stretching only if comfortable",
            "avoid": "All moderate to strenuous exercise",
            "duration": "Rest is more important than exercise at this stage"
        }
        plan["diet_and_hydration"] = {
            "fluids": "10-12 glasses of water daily, warm fluids for comfort",
            "foods": "Soft, nutritious foods: soup, oatmeal, bananas, rice, toast, broth",
            "avoid": "Heavy meals, alcohol, smoking, fried or spicy foods"
        }
        plan["when_to_seek_care"] = "If no improvement after 2-3 days, if symptoms worsen, or if fever exceeds 38.5°C"
        plan["estimated_recovery_time"] = "3-7 days depending on condition and adherence to care plan"
    
    # Symptom-specific additions
    specific_care = []
    if "fever" in symptoms_lc:
        specific_care.append({
            "symptom": "Fever",
            "care": "Cool compress on forehead, wear light clothing, keep room cool, tepid sponge bath if very uncomfortable"
        })
    if "cough" in symptoms_lc:
        specific_care.append({
            "symptom": "Cough",
            "care": "Humidifier or steam inhalation, honey (for adults) 1-2 tsp as needed, elevate head while sleeping"
        })
    if "sore throat" in symptoms_lc:
        specific_care.append({
            "symptom": "Sore throat",
            "care": "Warm salt water gargle every 3 hours, throat lozenges, warm tea with honey"
        })
    if "congestion" in symptoms_lc or "stuffy nose" in symptoms_lc:
        specific_care.append({
            "symptom": "Congestion",
            "care": "Steam inhalation 2-3 times daily, saline nasal rinse, sleep with head elevated"
        })
    if "body aches" in symptoms_lc or "muscle pain" in symptoms_lc:
        specific_care.append({
            "symptom": "Body aches",
            "care": "Warm bath or heating pad 15-20 minutes, gentle massage, adequate rest"
        })
    if "diarrhea" in symptoms_lc:
        specific_care.append({
            "symptom": "Diarrhea",
            "care": "BRAT diet (Bananas, Rice, Applesauce, Toast), avoid dairy, take ORS after each stool"
        })
    if "vomiting" in symptoms_lc:
        specific_care.append({
            "symptom": "Vomiting",
            "care": "Small sips of clear fluids, ginger tea, avoid solid foods until vomiting stops"
        })
    
    plan["symptom_specific_care"] = specific_care
    
    return plan

