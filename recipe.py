import os
import requests
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ——— Configuration ———
API_KEY = os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

st.set_page_config(page_title="Recipe Finder", page_icon="🍽️")
st.title("Recipe Finder")
st.write("Discover delicious recipes based on the ingredients you have on hand!")

# ——— Session State Initialization ———
if "recipes_data" not in st.session_state:
    st.session_state.recipes_data = []

# ——— Input Widgets ———
people_count = st.number_input(
    "Number of people",
    min_value=1,
    max_value=100,
    value=1,
    step=1,
    key="people_count",
)
ingredients = st.text_input(
    "Ingredients (comma-separated)",
    key="ingredients",
    placeholder="e.g. flour, eggs, milk",
)

# ——— Fetch Functions ———
def fetch_recipes(ingredients_str: str):
    """Call Spoonacular and return a list of recipe dicts."""
    params = {"apiKey": API_KEY, "ingredients": ingredients_str}
    resp = requests.get(f"{API_BASE_URL}/recipes/findByIngredients", params=params)
    resp.raise_for_status()
    return resp.json()

def fetch_nutrition(recipe_id: int) -> dict:
    """Call Spoonacular to get nutrition widget (macros)."""
    resp = requests.get(
        f"{API_BASE_URL}/recipes/{recipe_id}/nutritionWidget.json",
        params={"apiKey": API_KEY}
    )
    resp.raise_for_status()
    return resp.json()

# ——— Search Action ———
if st.button("Search Recipes"):
    ingr = ingredients.strip()
    if not ingr:
        st.warning("❗ Please enter at least one ingredient.")
    else:
        try:
            st.session_state.recipes_data = fetch_recipes(ingr)
        except requests.HTTPError as e:
            st.error(f"API Error: {e}")
            st.session_state.recipes_data = []

# ——— Display Results ———
recipes = st.session_state.recipes_data

if not isinstance(recipes, list) or not recipes:
    st.info("No recipes to show. Try searching with different ingredients.")
else:
    for recipe in recipes:
        st.subheader(recipe.get("title", "Untitled recipe"))
        col1, col2 = st.columns([1, 2])

        # — Left: used / missed / unused ingredients
        with col1:
            for kind in ("usedIngredients", "missedIngredients", "unusedIngredients"):
                items = recipe.get(kind, [])
                if items:
                    label = kind.replace("Ingredients", "")
                    st.markdown(f"**{label} Ingredients**")
                    for ing in items:
                        amt = round(people_count * ing.get("amount", 0), 2)
                        unit = ing.get("unitLong") or ing.get("unit") or ""
                        name = ing.get("originalName") or ing.get("name")
                        st.write(f"- {amt:g} {unit} {name}")

        # — Right: image, bar chart, and macro pie chart with totals
        with col2:
            # Recipe image
            if recipe.get("image"):
                st.image(
                    recipe["image"],
                    caption=recipe.get("title", ""),
                    use_container_width=True
                )

            # Ingredient bar chart
            combined = recipe.get("usedIngredients", []) + recipe.get("missedIngredients", [])
            data = {
                ing.get("originalName") or ing.get("name"): people_count * ing.get("amount", 0)
                for ing in combined
            }
            df = pd.DataFrame.from_dict(data, orient="index", columns=["Amount"])
            df.index.name = "Ingredient"
            st.bar_chart(df)

            # Macronutrient pie chart and totals
            try:
                nutrition = fetch_nutrition(recipe.get("id"))
                # parse numeric grams
                carbs = float(nutrition.get("carbs", "0g").rstrip("g")) * people_count
                protein = float(nutrition.get("protein", "0g").rstrip("g")) * people_count
                fat = float(nutrition.get("fat", "0g").rstrip("g")) * people_count

                macros = {"Carbs": carbs, "Protein": protein, "Fat": fat}
                # Split layout for chart and values
                pie_col, val_col = st.columns([1, 1])

                with pie_col:
                    fig, ax = plt.subplots()
                    # set white background
                    fig.patch.set_facecolor("white")
                    ax.set_facecolor("white")
                    ax.pie(
                        macros.values(),
                        labels=macros.keys(),
                        autopct="%1.1f%%",
                        startangle=90,
                    )
                    ax.set_title("Macronutrient Distribution")
                    ax.axis("equal")
                    st.pyplot(fig)

                with val_col:
                    st.markdown("**Total (g):**")
                    st.write(f"- Carbs: {carbs:.1f} g")
                    st.write(f"- Protein: {protein:.1f} g")
                    st.write(f"- Fat: {fat:.1f} g")

            except requests.HTTPError:
                st.warning("⚠️ Could not fetch nutrition info.")
