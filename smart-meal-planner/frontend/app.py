"""
Streamlit Frontend — Smart Meal Planner
Provides a clean UI for:
  1. Entering dietary preferences
  2. Viewing the generated meal plan
  3. Submitting feedback
"""

import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Smart Meal Planner",
    page_icon="🥗",
    layout="wide"
)


st.markdown("""
<style>
    .meal-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        border-left: 4px solid #28a745;
    }
    .metric-box {
        background: #e8f5e9;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
    .tag {
        background: #d4edda;
        color: #155724;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
        display: inline-block;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)


st.title("🥗 Smart Meal Planner")
st.caption("AI-powered personalized meal planning using Multi-Agent RAG")


with st.sidebar:
    st.header("Your Preferences")

    user_id = st.text_input("User ID", value="user_001", help="Your unique identifier")

    diet_type = st.selectbox(
        "Diet Type",
        options=["veg", "non-veg", "vegan"],
        index=0
    )

    calorie_limit = st.slider(
        "Daily Calorie Target",
        min_value=1200,
        max_value=4000,
        value=2000,
        step=50,
        help="Your total daily calorie goal"
    )

    st.subheader("Allergies")
    allergy_options = ["gluten", "dairy", "eggs", "nuts", "tree nuts", "soy", "fish", "sesame"]
    allergies = st.multiselect("Select allergens to avoid", options=allergy_options)

    st.subheader("Health Conditions")
    condition_options = ["diabetes", "hypertension", "heart disease", "obesity"]
    health_conditions = st.multiselect("Select your conditions", options=condition_options)

    st.divider()

    generate_btn = st.button("Generate Meal Plan", type="primary", use_container_width=True)




def render_meal_card(meal_type: str, meal: dict):
    """Render a single meal as a styled card."""
    icons = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙", "snack": "🍎"}
    icon = icons.get(meal_type, "🍽️")

    with st.container():
        st.markdown(f"### {icon} {meal_type.capitalize()}: {meal['name']}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calories", f"{meal['calories']} kcal")
        col2.metric("Protein", f"{meal['protein']}g")
        col3.metric("Carbs", f"{meal['carbs']}g")
        col4.metric("Fat", f"{meal['fat']}g")

        with st.expander("View Details"):
            st.write("**Ingredients:**", ", ".join(meal["ingredients"]))
            st.write("**Instructions:**", meal["instructions"])
            if meal.get("health_tags"):
                tags_html = " ".join(
                    f'<span class="tag">{t}</span>' for t in meal["health_tags"]
                )
                st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)

        st.divider()


def call_api(endpoint: str, method: str = "GET", payload: dict = None):
    """Make an API call to the backend with error handling."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=60)
        else:
            resp = requests.get(url, params=payload, timeout=60)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Make sure the FastAPI server is running on port 8000."
    except requests.exceptions.Timeout:
        return None, "Request timed out. The AI pipeline may be loading models — try again."
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, f"API Error: {detail}"



if generate_btn:
    if not user_id.strip():
        st.error("Please enter a User ID.")
    else:
        
        with st.spinner("Saving your preferences..."):
            payload = {
                "user_id": user_id,
                "diet_type": diet_type,
                "calorie_limit": calorie_limit,
                "allergies": allergies,
                "health_conditions": health_conditions
            }
            result, err = call_api("/user-input", method="POST", payload=payload)
            if err:
                st.error(err)
                st.stop()

       
        with st.spinner("Running AI agents to build your meal plan... (this may take 10-30s)"):
            plan_data, err = call_api("/meal-plan", method="GET", payload={"user_id": user_id})
            if err:
                st.error(err)
                st.stop()

      
        st.session_state["meal_plan"] = plan_data
        st.session_state["user_id"] = user_id
        st.success("Meal plan generated!")



if "meal_plan" in st.session_state:
    data = st.session_state["meal_plan"]
    mp = data["meal_plan"]

    st.subheader("Daily Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Calories", f"{mp['total_calories']} kcal")
    c2.metric("Protein", f"{mp['total_protein']}g")
    c3.metric("Carbs", f"{mp['total_carbs']}g")
    c4.metric("Fat", f"{mp['total_fat']}g")
    c5.metric("AI Score", f"{data['personalization_score']:.0%}")

   
    if data["validation_passed"]:
        st.success("✅ Meal plan passed all health and safety checks.")
    else:
        st.warning("⚠️ Meal plan has some issues — see notes below.")

    if data.get("validation_notes"):
        with st.expander("Validation Notes"):
            for note in data["validation_notes"]:
                st.write(f"• {note}")

  
    if mp.get("notes"):
        st.info(f"💡 {mp['notes']}")

    st.divider()

 
    st.subheader("Your Meal Plan")
    for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
        render_meal_card(meal_type, mp[meal_type])

    st.subheader("Rate This Meal Plan")
    with st.form("feedback_form"):
        rating = st.slider("Rating", min_value=1, max_value=5, value=4)
        comments = st.text_area("Comments (optional)", placeholder="What did you like or dislike?")
        submit_feedback = st.form_submit_button("Submit Feedback")

        if submit_feedback:
            fb_payload = {
                "user_id": st.session_state.get("user_id", "anonymous"),
                "rating": rating,
                "comments": comments
            }
            result, err = call_api("/feedback", method="POST", payload=fb_payload)
            if err:
                st.error(err)
            else:
                st.success(result.get("message", "Feedback submitted!"))

else:
 
    st.info(
        "👈 Fill in your dietary preferences in the sidebar and click **Generate Meal Plan** to get started."
    )

    st.subheader("How It Works")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**1. Input Agent**\nValidates your dietary preferences and health conditions.")
    with col2:
        st.markdown("**2. Retrieval Agent**\nSearches a recipe database using AI-powered semantic search (RAG).")
    with col3:
        st.markdown("**3. Nutrition Agent**\nAssembles a balanced daily meal plan with macro analysis.")
    with col4:
        st.markdown("**4. Validation Agent**\nChecks allergens, diet compliance, and calorie targets.")
