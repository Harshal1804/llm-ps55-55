
import os
import json
import streamlit as st
import pandas as pd

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ----------------------------------
# 1. Application Configuration
# ----------------------------------

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

st.set_page_config(
    page_title="Fitness Routine Planner",
    page_icon="💪",
    layout="wide"
)


# ----------------------------------
# 2. Page Header
# ----------------------------------

st.title("💪 Fitness Routine Planner")

st.write(
    "Your personal AI-powered home workout assistant. "
    "Create a workout plan based on your goals, fitness level "
    "and available equipment."
)

st.divider()


# ----------------------------------
# 3. User Input Form
# ----------------------------------

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
                "Flexibility and Mobility"
            ]
        )

        level = st.selectbox(
            "Select your fitness level",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ]
        )

    with col2:

        minutes = st.selectbox(
            "Available time per day (minutes)",
            [15, 30, 45, 60]
        )

        equipment = st.multiselect(
            "Available equipment",
            [
                "No equipment (bodyweight only)",
                "Yoga Mat",
                "Dumbbells",
                "Resistance Bands",
                "Chair",
                "Skipping Rope"
            ],
            default=["No equipment (bodyweight only)"]
        )

    limitations = st.text_input(
        "Any injuries or physical limitations? (Optional)",
        placeholder="Example: Knee pain, back discomfort, etc."
    )

    submitted = st.form_submit_button(
        "🚀 Generate My Weekly Plan",
        use_container_width=True
    )


# ----------------------------------
# 4. Generate LLM Prompt
# ----------------------------------

def create_prompt(goal, level, minutes, equipment, limitations):

    equipment_text = (
        ", ".join(equipment)
        if equipment
        else "No equipment (bodyweight only)"
    )

    prompt = f"""
You are a careful and knowledgeable home fitness
planning assistant.

Create a personalised seven-day home workout plan.

USER DETAILS:

Fitness Goal: {goal}
Fitness Level: {level}
Available Time Per Day: {minutes} minutes
Available Equipment: {equipment_text}
Injuries or Limitations: {limitations if limitations else "None stated"}

INSTRUCTIONS:

1. Generate exactly seven days, Monday through Sunday.
2. Make the plan suitable for the selected fitness level.
3. Respect the user's daily time availability.
4. Use only the available equipment.
5. Include at least one complete rest day.
6. Include appropriate sets and repetitions or exercise duration.
7. Specify rest time between exercise sets in seconds.
8. Include a warm-up and cool-down for workout days.
9. Include recovery recommendations.
10. Avoid excessive intensity and unrealistic exercise volumes.
11. Do not recommend exercises that conflict with stated
    injuries or limitations. If a limitation is reported,
    explain that professional medical guidance is needed
    before following the plan.
12. Do not claim that the plan treats or cures any condition.
13. Keep the exercises practical for a home environment.
14. The workout duration must not exceed the user's
    available time, including warm-up and cool-down.

OUTPUT FORMAT:

Return valid JSON only, with this structure:

{{
  "weekly_plan": [
    {{
      "day": "Monday",
      "focus": "Upper Body",
      "duration_minutes": 30,
      "is_rest_day": false,
      "warm_up": "5 minutes of gentle movement",
      "exercises": [
        {{
          "name": "Wall Push-ups",
          "sets": 3,
          "reps_or_duration": "10 repetitions",
          "rest_seconds": 60,
          "form_tip": "Keep your body straight."
        }}
      ],
      "cool_down": "Gentle stretching",
      "recovery_note": "Stay hydrated."
    }}
  ]
}}

Make sure the JSON contains exactly seven day objects.
Return no Markdown or additional text.
"""

    return prompt


# ----------------------------------
# 5. Call Gemini API
# ----------------------------------

def generate_workout_plan(prompt):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "Gemini API key not found. Check your .env file."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60000,
            retry_options=types.HttpRetryOptions(
                attempts=1
            )
        )
    )

    try:

        response = client.models.generate_content(

            model=MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
                max_output_tokens=6000
            )
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        result = json.loads(response.text)

        weekly_plan = result.get("weekly_plan")

        if not isinstance(weekly_plan, list) or len(weekly_plan) != 7:
            raise ValueError(
                "Gemini did not return a complete seven-day plan."
            )

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

            rows.append({
                "Day": day.get("day", ""),
                "Focus": day.get("focus", "Rest and Recovery"),
                "Duration": "Rest",
                "Exercise": "Full Rest Day",
                "Sets": "-",
                "Reps / Duration": "-",
                "Rest (seconds)": "-",
                "Form Tip": "Prioritise recovery."
            })

            continue

        exercises = day.get("exercises", [])

        if not isinstance(exercises, list):
            raise ValueError("Invalid exercise data received.")

        for exercise in exercises:

            rows.append({
                "Day": day.get("day", ""),
                "Focus": day.get("focus", ""),
                "Duration": f"{day.get('duration_minutes', 0)} min",
                "Exercise": exercise.get("name", ""),
                "Sets": exercise.get("sets", "-"),
                "Reps / Duration": exercise.get(
                    "reps_or_duration", "-"
                ),
                "Rest (seconds)": exercise.get(
                    "rest_seconds", "-"
                ),
                "Form Tip": exercise.get("form_tip", "")
            })

    return pd.DataFrame(rows)


# ----------------------------------
# 7. Handle Generate Button
# ----------------------------------

if submitted:

    if not equipment:
        st.warning("Please select your available equipment.")

    else:

        # Avoid conflicting equipment selections
        selected_equipment = [
            item for item in equipment
            if item != "No equipment (bodyweight only)"
        ]

        if not selected_equipment and (
            "No equipment (bodyweight only)" in equipment
        ):
            selected_equipment = ["No equipment (bodyweight only)"]

        prompt = create_prompt(
            goal,
            level,
            minutes,
            selected_equipment,
            limitations
        )

        st.session_state.pop("weekly_plan", None)

        try:

            with st.spinner(
                "🤖 Gemini is creating your personalised workout plan..."
            ):

                plan = generate_workout_plan(prompt)

            st.session_state.weekly_plan = plan

            st.success("Your weekly workout plan is ready!")

        except Exception as error:

            error_text = str(error)

            if "503" in error_text or "UNAVAILABLE" in error_text:
                st.error(
                    "Gemini is temporarily unavailable. "
                    "Please try again shortly."
                )

            elif "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                st.error(
                    "Gemini API rate limit reached. "
                    "Please try again later."
                )

            else:
                st.error(f"Unable to generate the plan: {error_text}")


# ----------------------------------
# 8. Display Generated Workout Plan
# ----------------------------------

if "weekly_plan" in st.session_state:

    plan = st.session_state.weekly_plan

    st.divider()

    st.subheader("📅 Your 7-Day Workout Schedule")

    st.write(
        "Here is your personalised workout plan. "
        "Follow the exercises and rest intervals listed below."
    )

    df = create_workout_table(plan)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Daily Warm-up and Recovery Guide")

    for day in plan:

        with st.expander(
            f"{day.get('day', 'Day')} — {day.get('focus', '')}"
        ):

            if day.get("is_rest_day"):

                st.info("Rest day. Allow your body to recover.")

            else:

                st.write("**Warm-up:**", day.get("warm_up", "Not specified"))

                st.write(
                    "**Cool-down:**",
                    day.get("cool_down", "Not specified")
                )

            st.write(
                "**Recovery:**",
                day.get("recovery_note", "Not specified")
            )

    st.download_button(
        label="⬇️ Download Workout Plan (CSV)",
        data=df.to_csv(index=False),
        file_name="weekly_workout_plan.csv",
        mime="text/csv"
    )

    st.caption(
        "Disclaimer: This is an AI-generated fitness plan, "
        "not medical advice. Stop exercising if you experience "
        "pain or concerning symptoms. Seek qualified guidance "
        "for injuries or medical limitations."
    )
