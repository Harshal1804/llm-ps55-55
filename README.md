# 💪 Fitness Routine Planner

**LLM Mini Project | Problem Statement 55**

An AI-powered home workout planner that uses Google Gemini to generate a personalised seven-day fitness routine based on the user's fitness goal, experience level, available time, equipment, and optional physical limitations.

**Student:** Harshal Shinde  
**Roll Number:** 55  
**Class/Division:** LYCore 5  
**GitHub:** https://github.com/Harshal1804/llm-ps55-55

---

## 1. Problem Statement

Planning a balanced weekly workout can be difficult for people who are new to home fitness. A suitable routine depends on several factors, including the person's fitness goal, experience level, time available each day, equipment at home, and any physical limitations.

The Fitness Routine Planner addresses this problem by accepting these preferences and using a Large Language Model (LLM) to generate a structured seven-day home workout schedule. The application validates the generated data and presents it through an interactive interface.

## 2. Project Objectives

- Generate a personalised workout schedule covering Monday through Sunday.
- Adapt exercise selection to the user's fitness goal and experience level.
- Respect the user's daily time limit and selected equipment.
- Include exercise details, sets, repetitions, rest intervals, and form tips.
- Provide warm-up, cool-down, rest-day, and recovery recommendations.
- Use structured LLM output and Python validation to reduce incomplete or inconsistent plans.
- Provide a downloadable CSV version of the generated schedule.

## 3. Features

### Personalised User Inputs

| Input | Available Options |
|---|---|
| Fitness Goal | Weight Loss, Muscle Gain, General Fitness, Flexibility and Mobility |
| Fitness Level | Beginner, Intermediate, Advanced |
| Available Time | 15, 30, 45, or 60 minutes per day |
| Equipment | Bodyweight only, Yoga Mat, Dumbbells, Resistance Bands, Chair, Skipping Rope |
| Physical Limitations | Optional field for injuries or physical limitations |

### Generated Workout Plan

- Personalised seven-day workout schedule.
- At least one complete rest day.
- Daily workout focus and duration.
- Warm-up, main workout, and cool-down duration breakdown.
- Exercise names, sets, repetitions or duration, and rest intervals.
- Equipment information for each exercise.
- Exercise form tips.
- Daily recovery recommendations.
- Expandable day-by-day workout details.
- Weekly workout table.
- CSV download functionality.

### Goal-Specific Workout Planning

The application uses separate prompt instructions for each fitness goal.

**Weight Loss**
- Practical full-body workouts.
- Strength exercises and appropriately scaled cardio.
- Low-impact alternatives.

**Muscle Gain**
- Home-based resistance training.
- Muscle-strengthening exercises.
- Suitable sets, repetitions, and recovery intervals.

**General Fitness**
- Balanced strength training.
- Cardiovascular fitness and endurance.
- Mobility exercises.

**Flexibility and Mobility**
- Stretching and joint mobility.
- Controlled movements and balance.
- Breathing exercises.
- Restrictions against selected high-intensity and cardio-oriented exercises.

## 4. System Workflow

The application follows this workflow:

1. The user opens the Streamlit application.
2. The user enters fitness preferences.
3. Python constructs a personalised prompt.
4. The prompt is sent to Google Gemini through the Google Gen AI SDK.
5. Gemini generates a structured JSON workout plan.
6. Python parses and validates the generated response.
7. Pandas converts the workout data into a table.
8. Streamlit displays the weekly schedule and daily workout details.
9. The user can download the schedule as a CSV file.

### Architecture Diagram

```mermaid
flowchart TD
    A[User] --> B[Streamlit Interface]
    B --> C[User Fitness Preferences]
    C --> D[Python Prompt Engineering]
    D --> E[Google Gemini API]
    E --> F[Structured JSON Response]
    F --> G[Python Validation]
    G --> H{Valid Workout Plan?}
    H -->|No| I[Display Error Message]
    H -->|Yes| J[Pandas Data Processing]
    J --> K[Weekly Workout Schedule]
    K --> L[Daily Workout Details]
    K --> M[CSV Download]
