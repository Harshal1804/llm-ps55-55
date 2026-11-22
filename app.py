import json
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ----------------------------------
# 1. Application Configuration
# ----------------------------------

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
NO_EQUIPMENT_OPTION = "No equipment (bodyweight only)"

st.set_page_config(
    page_title="Fitness Routine Planner",
    page_icon="💪",
    layout="wide",
)


# ----------------------------------
# 2. Helper Functions
# ----------------------------------

def normalize_equipment(selected_equipment):
    """Remove the bodyweight-only placeholder when real equipment is selected."""
    physical_equipment = [
        item for item in selected_equipment
        if item != NO_EQUIPMENT_OPTION
    ]

    if physical_equipment:
        return physical_equipment

    return [NO_EQUIPMENT_OPTION]


def get_allowed_equipment(selected_equipment):
    """Return equipment Gemini may assign to an exercise."""
    allowed = {"Bodyweight"}

    if NO_EQUIPMENT_OPTION not in selected_equipment:
        allowed.update(selected_equipment)

    return allowed


# ----------------------------------
# 3. Generate LLM Prompt
# ----------------------------------

def create_prompt(goal, level, minutes, equipment, limitations):
    if NO_EQUIPMENT_OPTION in equipment:
        equipment_text = "Bodyweight only; no external equipment"
    else:
        equipment_text = ", ".join(equipment)

    goal_guidelines = {
        "Weight Loss": """
Focus on practical full-body workouts combining strength exercises
and appropriately scaled cardio. Include low-impact alternatives.
Do not promise a specific amount of weight loss or claim to target
fat loss in particular body areas.
""",
        "Muscle Gain": """
Focus on home-based resistance training and muscle-strengthening
exercises. Use suitable sets, repetitions and rest intervals.
Distribute muscle groups sensibly and allow recovery between
sessions that train the same muscle groups.
""",
        "General Fitness": """
Create a balanced combination of strength, cardiovascular fitness,
endurance and mobility. Distribute different activities throughout
the week and include appropriate recovery.
""",
        "Flexibility and Mobility": """
Prioritise stretching, joint mobility, controlled movement, balance
and breathing exercises. Do not include skipping rope, jump rope,
jumping jacks, burpees, sprinting or high-intensity cardio as workout
exercises. Do not turn this into a cardio or weight-training plan.
""",
    }

    prompt = f"""
You are a careful home fitness workout planning assistant.
Create a personalised, realistic seven-day home workout plan.

USER PROFILE:
Fitness Goal: {goal}
Fitness Level: {level}
Maximum Available Time Per Day: {minutes} minutes
Available Equipment: {equipment_text}
Physical Limitations: {limitations.strip() if limitations and limitations.strip() else "None stated"}

GOAL-SPECIFIC GUIDANCE:
{goal_guidelines[goal]}

GENERAL RULES:
1. Generate exactly seven days, Monday through Sunday, in that order.
2. Include at least one complete rest day.
3. Match every workout to the selected fitness goal and level.
4. Beginner plans must use simple, easy-to-follow exercises.
5. Use only the listed equipment. Bodyweight exercises are always allowed.
6. Never assume the user owns equipment that was not selected.
7. Each exercise must include its name, sets, repetitions or duration,
   rest interval in seconds, equipment used, and a short form tip.
8. Each workout day must stay within {minutes} minutes total.
9. The total time must include warm-up, main workout and cool-down.
10. The duration breakdown must add up exactly to duration_minutes.
11. Include a warm-up and cool-down for every workout day.
12. Distribute training and recovery sensibly across the week.
13. Keep exercises practical for a home environment.
14. Do not diagnose injuries or claim an exercise is medically safe.
    When a limitation is supplied, avoid exercises that directly stress
    the stated problem area and recommend qualified professional guidance.
15. Do not make medical claims or guarantee fitness outcomes.

OUTPUT FORMAT:
Return valid JSON only, with this exact overall structure:

{{
  "weekly_plan": [
    {{
      "day": "Monday",
      "focus": "Upper Body Strength",
      "duration_minutes": 30,
      "duration_breakdown": {{
        "warm_up_minutes": 5,
        "main_workout_minutes": 20,
        "cool_down_minutes": 5
      }},
      "is_rest_day": false,
      "warm_up": "5 minutes of gentle movement",
      "exercises": [
        {{
          "name": "Wall Push-ups",
          "sets": 3,
          "reps_or_duration": "10 repetitions",
          "rest_seconds": 60,
          "equipment_used": ["Bodyweight"],
          "form_tip": "Maintain a straight body position."
        }}
      ],
      "cool_down": "Gentle upper body stretching",
      "recovery_note": "Stay hydrated and allow muscles to recover."
    }}
  ]
}}

REST DAY RULES:
- is_rest_day must be true.
- duration_minutes must be 0.
- All duration_breakdown values must be 0.
- exercises must be an empty list.
- focus must be exactly "Rest and Recovery".
- Include a recovery_note.

WORKOUT DAY RULES:
- is_rest_day must be false.
- duration_minutes must be a positive integer no greater than {minutes}.
- warm_up_minutes + main_workout_minutes + cool_down_minutes
  must equal duration_minutes.
- Include at least one exercise.
- Every exercise must have a non-empty equipment_used list containing
  only selected equipment or "Bodyweight".
- Every exercise must include a non-empty form_tip.

ALLOWED EQUIPMENT:
{equipment_text}
Bodyweight is always allowed.

Return exactly seven day objects. Do not include Markdown fences,
comments, explanations, or additional text outside the JSON.
"""

    return prompt


# ----------------------------------
# 4. Validate Gemini Output
# ----------------------------------

def validate_workout_plan(weekly_plan, available_minutes, selected_equipment, goal):
    expected_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    if not isinstance(weekly_plan, list) or len(weekly_plan) != 7:
        raise ValueError("The plan must contain exactly seven days.")

    if not all(isinstance(day, dict) for day in weekly_plan):
        raise ValueError("One or more day entries are not valid objects.")

    actual_days = [day.get("day") for day in weekly_plan]
    if actual_days != expected_days:
        raise ValueError("The weekdays are missing or incorrectly ordered.")

    rest_days = [day for day in weekly_plan if day.get("is_rest_day") is True]
    if not rest_days:
        raise ValueError("The plan must include at least one complete rest day.")

    allowed_equipment = get_allowed_equipment(selected_equipment)

    restricted_flexibility_exercises = [
        "skipping",
        "jump rope",
        "jumping rope",
        "jumping jack",
        "burpee",
        "sprint",
        "high knees",
        "mountain climber",
    ]
    restricted_flexibility_focus = [
        "cardio",
        "interval training",
        "endurance training",
        "weight training",
    ]

    for day in weekly_plan:
        day_name = day["day"]
        duration = day.get("duration_minutes")
        exercises = day.get("exercises")
        breakdown = day.get("duration_breakdown")
        is_rest_day = day.get("is_rest_day")

        if not isinstance(is_rest_day, bool):
            raise ValueError(f"{day_name}: is_rest_day must be true or false.")

        if is_rest_day:
            if duration != 0 or exercises != []:
                raise ValueError(
                    f"{day_name}: A rest day must have zero duration and no exercises."
                )

            expected_rest_breakdown = {
                "warm_up_minutes": 0,
                "main_workout_minutes": 0,
                "cool_down_minutes": 0,
            }
            if breakdown != expected_rest_breakdown:
                raise ValueError(f"{day_name}: Rest day duration breakdown is invalid.")

            if day.get("focus") != "Rest and Recovery":
                raise ValueError(f"{day_name}: Rest day focus must be 'Rest and Recovery'.")

            if not isinstance(day.get("recovery_note"), str) or not day["recovery_note"].strip():
                raise ValueError(f"{day_name}: Rest day recovery note is missing.")

            continue

        if not isinstance(duration, int) or isinstance(duration, bool):
            raise ValueError(f"{day_name}: Workout duration must be an integer.")

        if duration <= 0 or duration > available_minutes:
            raise ValueError(
                f"{day_name}: Workout duration exceeds your available time."
            )

        if not isinstance(day.get("focus"), str) or not day["focus"].strip():
            raise ValueError(f"{day_name}: Workout focus is missing.")

        required_parts = [
            "warm_up_minutes",
            "main_workout_minutes",
            "cool_down_minutes",
        ]

        if not isinstance(breakdown, dict):
            raise ValueError(f"{day_name}: Missing duration breakdown.")

        for part in required_parts:
            value = breakdown.get(part)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{day_name}: Invalid value for {part}.")

        if breakdown["main_workout_minutes"] <= 0:
            raise ValueError(f"{day_name}: Main workout time must be greater than zero.")

        if sum(breakdown[part] for part in required_parts) != duration:
            raise ValueError(
                f"{day_name}: Duration breakdown does not add up to the total duration."
            )

        if not isinstance(day.get("warm_up"), str) or not day["warm_up"].strip():
            raise ValueError(f"{day_name}: Warm-up instructions are missing.")

        if not isinstance(day.get("cool_down"), str) or not day["cool_down"].strip():
            raise ValueError(f"{day_name}: Cool-down instructions are missing.")

        if not isinstance(day.get("recovery_note"), str) or not day["recovery_note"].strip():
            raise ValueError(f"{day_name}: Recovery note is missing.")

        if not isinstance(exercises, list) or not exercises:
            raise ValueError(f"{day_name}: At least one exercise is required.")

        if goal == "Flexibility and Mobility":
            focus_lower = day["focus"].lower()
            if any(term in focus_lower for term in restricted_flexibility_focus):
                raise ValueError(
                    f"{day_name}: The workout focus does not match the flexibility goal."
                )

        for exercise in exercises:
            if not isinstance(exercise, dict):
                raise ValueError(f"{day_name}: Invalid exercise entry.")

            name = exercise.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{day_name}: An exercise name is missing.")

            sets = exercise.get("sets")
            if not isinstance(sets, int) or isinstance(sets, bool) or sets < 1:
                raise ValueError(f"{name}: Number of sets must be a positive integer.")

            rest = exercise.get("rest_seconds")
            if not isinstance(rest, int) or isinstance(rest, bool) or rest < 0:
                raise ValueError(f"{name}: Rest interval must be a non-negative integer.")

            reps_or_duration = exercise.get("reps_or_duration")
            if not isinstance(reps_or_duration, str) or not reps_or_duration.strip():
                raise ValueError(f"{name}: Repetitions or duration are missing.")

            form_tip = exercise.get("form_tip")
            if not isinstance(form_tip, str) or not form_tip.strip():
                raise ValueError(f"{name}: Form tip is missing.")

            used_equipment = exercise.get("equipment_used")
            if not isinstance(used_equipment, list) or not used_equipment:
                raise ValueError(f"{name}: Equipment information must be a non-empty list.")

            if not all(isinstance(item, str) for item in used_equipment):
                raise ValueError(f"{name}: Equipment entries must be text values.")

            if not set(used_equipment).issubset(allowed_equipment):
                unexpected = sorted(set(used_equipment) - allowed_equipment)
                raise ValueError(
                    f"{name}: Uses equipment you did not select: {', '.join(unexpected)}."
                )

            if goal == "Flexibility and Mobility":
                name_lower = name.lower()
                if any(term in name_lower for term in restricted_flexibility_exercises):
                    raise ValueError(
                        f"{name}: This exercise does not match the flexibility goal."
                    )

    return True


# ----------------------------------
# 5. Call Gemini API
# ----------------------------------

def generate_workout_plan(prompt):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Gemini API key not found. Check your .env file.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=6000,
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as error:
            raise ValueError("Gemini returned invalid JSON. Please generate the plan again.") from error

        if not isinstance(result, dict):
            raise ValueError("Gemini response must be a JSON object.")

        weekly_plan = result.get("weekly_plan")
        if not isinstance(weekly_plan, list):
            raise ValueError("Gemini response is missing the weekly_plan list.")

        return weekly_plan

    finally:
        client.close()


# ----------------------------------
# 6. Convert Plan into a Table
# ----------------------------------

def create_workout_table(weekly_plan):
    rows = []

    for day in weekly_plan:
        if day.get("is_rest_day"):
            rows.append(
                {
                    "Day": day["day"],
                    "Focus": "Rest and Recovery",
                    "Duration": "Rest",
                    "Exercise": "Full Rest Day",
                    "Equipment": "-",
                    "Sets": "-",
                    "Reps / Duration": "-",
                    "Rest (seconds)": "-",
                }
            )
            continue

        for exercise in day.get("exercises", []):
            equipment_used = exercise.get("equipment_used", [])
            rows.append(
                {
                    "Day": day["day"],
                    "Focus": day.get("focus", ""),
                    "Duration": f"{day['duration_minutes']} min",
                    "Exercise": exercise.get("name", ""),
                    "Equipment": ", ".join(equipment_used) if equipment_used else "None",
                    "Sets": exercise.get("sets", "-"),
                    "Reps / Duration": exercise.get("reps_or_duration", "-"),
                    "Rest (seconds)": exercise.get("rest_seconds", "-"),
                }
            )

    return pd.DataFrame(rows)


# ----------------------------------
# 7. Page Header and User Input Form
# ----------------------------------

st.title("💪 Fitness Routine Planner")
st.write(
    "Your personal AI-powered home workout assistant. Create a workout plan "
    "based on your goals, fitness level and available equipment."
)
st.divider()
st.subheader("Personalise Your Workout")

with st.form("fitness_form"):
    col1, col2 = st.columns(2)

    with col1:
        goal = st.selectbox(
            "What is your fitness goal?",
            [
                "Weight Loss",
                "Muscle Gain",
                "General Fitness",
                "Flexibility and Mobility",
            ],
        )

        level = st.selectbox(
            "Select your fitness level",
            ["Beginner", "Intermediate", "Advanced"],
        )

    with col2:
        minutes = st.selectbox(
            "Available time per day (minutes)",
            [15, 30, 45, 60],
        )

        equipment = st.multiselect(
            "Available equipment",
            [
                NO_EQUIPMENT_OPTION,
                "Yoga Mat",
                "Dumbbells",
                "Resistance Bands",
                "Chair",
                "Skipping Rope",
            ],
            default=[NO_EQUIPMENT_OPTION],
            help=(
                "Select the equipment you have. If you select actual equipment "
                "alongside the bodyweight-only option, the actual equipment "
                "selection will be used; bodyweight exercises are always allowed."
            ),
        )

    limitations = st.text_input(
        "Any injuries or physical limitations? (Optional)",
        placeholder="Example: Knee pain, back discomfort, etc.",
    )

    submitted = st.form_submit_button(
        "🚀 Generate My Weekly Plan",
        use_container_width=True,
    )


# ----------------------------------
# 8. Handle Generate Button
# ----------------------------------

if submitted:
    if not equipment:
        st.warning("Please select your available equipment, or select bodyweight only.")
    else:
        selected_equipment = normalize_equipment(equipment)
        prompt = create_prompt(
            goal,
            level,
            minutes,
            selected_equipment,
            limitations,
        )

        # Remove a previous plan so an invalid new response is not shown as current.
        st.session_state.pop("weekly_plan", None)

        try:
            with st.spinner("🤖 Gemini is creating your personalised workout plan..."):
                plan = generate_workout_plan(prompt)
                validate_workout_plan(
                    plan,
                    minutes,
                    selected_equipment,
                    goal,
                )

            st.session_state["weekly_plan"] = plan
            st.success("Your weekly workout plan is ready!")

        except Exception as error:
            error_text = str(error)
            error_upper = error_text.upper()

            if "503" in error_text or "UNAVAILABLE" in error_upper:
                st.error("Gemini is temporarily unavailable. Please try again shortly.")
            elif "429" in error_text or "RESOURCE_EXHAUSTED" in error_upper:
                st.error("Gemini API rate limit reached. Please try again later.")
            elif "401" in error_text or "403" in error_text or "PERMISSION_DENIED" in error_upper:
                st.error("Gemini rejected the API request. Check that your API key is valid and has access to this model.")
            else:
                st.error(f"Unable to generate a valid workout plan: {error_text}")
                st.info("You can try generating the plan again. If the same validation error repeats, the prompt may need further adjustment.")


# ----------------------------------
# 9. Display Generated Workout Plan
# ----------------------------------

if "weekly_plan" in st.session_state:
    plan = st.session_state["weekly_plan"]
    workout_days = sum(1 for day in plan if not day.get("is_rest_day"))
    rest_days = sum(1 for day in plan if day.get("is_rest_day"))

    st.divider()
    st.subheader("📅 Your 7-Day Workout Schedule")
    st.write(
        "Here is your personalised workout plan. Follow the exercises and "
        "rest intervals listed below."
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Total days", "7")
    metric2.metric("Workout days", str(workout_days))
    metric3.metric("Rest days", str(rest_days))

    df = create_workout_table(plan)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(720, 42 + (len(df) * 36)),
        column_config={
            "Day": st.column_config.TextColumn("Day", width="small"),
            "Focus": st.column_config.TextColumn("Focus", width="medium"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Exercise": st.column_config.TextColumn("Exercise", width="medium"),
            "Equipment": st.column_config.TextColumn("Equipment", width="medium"),
            "Sets": st.column_config.TextColumn("Sets", width="small"),
            "Reps / Duration": st.column_config.TextColumn("Reps / Duration", width="medium"),
            "Rest (seconds)": st.column_config.TextColumn("Rest (seconds)", width="small"),
        },
    )

    st.subheader("Daily Warm-up, Exercise Form and Recovery Guide")

    for day in plan:
        with st.expander(f"{day.get('day')} — {day.get('focus')}"):
            if day.get("is_rest_day"):
                st.info("Rest day. Allow your body to recover.")
            else:
                breakdown = day.get("duration_breakdown", {})
                warm_up_minutes = breakdown.get("warm_up_minutes", 0)
                main_minutes = breakdown.get("main_workout_minutes", 0)
                cool_down_minutes = breakdown.get("cool_down_minutes", 0)

                time_col1, time_col2, time_col3 = st.columns(3)
                time_col1.metric("Warm-up", f"{warm_up_minutes} min")
                time_col2.metric("Main workout", f"{main_minutes} min")
                time_col3.metric("Cool-down", f"{cool_down_minutes} min")

                st.write("**Warm-up:**", day.get("warm_up"))

                exercise_details = []
                for exercise in day.get("exercises", []):
                    used_equipment = exercise.get("equipment_used", [])
                    exercise_details.append(
                        {
                            "Exercise": exercise.get("name", ""),
                            "Sets": exercise.get("sets", "-"),
                            "Reps / Duration": exercise.get("reps_or_duration", "-"),
                            "Rest (seconds)": exercise.get("rest_seconds", "-"),
                            "Equipment": ", ".join(used_equipment) if used_equipment else "None",
                            "Form Tip": exercise.get("form_tip", ""),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(exercise_details),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Exercise": st.column_config.TextColumn("Exercise", width="medium"),
                        "Form Tip": st.column_config.TextColumn("Form Tip", width="large"),
                    },
                )

                st.write("**Cool-down:**", day.get("cool_down"))

            st.write("**Recovery:**", day.get("recovery_note", "Not specified"))

    st.download_button(
        label="⬇️ Download Workout Plan (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="weekly_workout_plan.csv",
        mime="text/csv",
    )

    st.caption(
        "Disclaimer: This is an AI-generated fitness plan, not medical advice. "
        "Stop exercising if you experience pain or concerning symptoms. "
        "Seek qualified guidance for injuries or medical limitations."
    )


# ----------------------------------
# 10. Footer
# ----------------------------------

st.divider()
st.caption("Fitness Routine Planner | Powered by Python, Streamlit and Gemini")
