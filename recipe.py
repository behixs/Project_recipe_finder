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
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "show_favorites" not in st.session_state:
    st.session_state.show_favorites = False
if "display_count" not in st.session_state:
    st.session_state.display_count = 10
if "people_count" not in st.session_state:
    st.session_state.people_count = 1
if "recipe_nutrition" not in st.session_state:
    st.session_state.recipe_nutrition = {}

# ——— Input Widgets ———
sort_options = [
    "None",
    "Calories (low to high)", "Calories (high to low)",
    "Carbs (low to high)", "Carbs (high to low)",
    "Protein (low to high)", "Protein (high to low)",
    "Fat (low to high)", "Fat (high to low)"
]

if not st.session_state.show_favorites:
    st.session_state.people_count = st.number_input(
        "Number of people",
        min_value=1,
        max_value=100,
        value=st.session_state.people_count,
        step=1,
    )
    ingredients = st.text_input(
        "Ingredients (comma-separated)",
        key="ingredients",
        placeholder="e.g. flour, eggs, milk",
    )
    sort_option = st.selectbox("Sort recipes by", sort_options)
else:
    sort_option = "None"

# ——— Fetch Functions ———
def fetch_recipes(ingredients_str: str):
    params = {"apiKey": API_KEY, "ingredients": ingredients_str, "number": 50}
    resp = requests.get(f"{API_BASE_URL}/recipes/findByIngredients", params=params)
    resp.raise_for_status()
    return resp.json()

def fetch_nutrition(recipe_id: int) -> dict:
    resp = requests.get(
        f"{API_BASE_URL}/recipes/{recipe_id}/nutritionWidget.json",
        params={"apiKey": API_KEY}
    )
    resp.raise_for_status()
    return resp.json()

# ——— Buttons for View Toggle ———
if st.session_state.show_favorites:
    if st.button("🔍 Back to Search"):
        st.session_state.show_favorites = False
        st.session_state.display_count = 10
else:
    if st.button("⭐ Show Favorites"):
        st.session_state.show_favorites = True

# ——— Search Action ———
if not st.session_state.show_favorites and st.button("Search Recipes"):
    ingr = st.session_state.ingredients.strip()
    if not ingr:
        st.warning("❗ Please enter at least one ingredient.")
    else:
        try:
            st.session_state.recipes_data = fetch_recipes(ingr)
            st.session_state.display_count = 10
        except requests.HTTPError as e:
            st.error(f"API Error: {e}")
            st.session_state.recipes_data = []

# ——— Display Section ———
if st.session_state.show_favorites:
    st.header("⭐ Favorite Recipes")
    recipes = st.session_state.favorites
else:
    recipes = st.session_state.recipes_data[:st.session_state.display_count]

# Nutrition-based sorting preparation
for recipe in recipes:
    rid = recipe["id"]
    if rid not in st.session_state.recipe_nutrition:
        try:
            nutrition = fetch_nutrition(rid)
            st.session_state.recipe_nutrition[rid] = {
                "calories": float(nutrition.get("calories", "0").replace("kcal", "").strip()),
                "carbs": float(nutrition.get("carbs", "0g").replace("g", "").strip()),
                "protein": float(nutrition.get("protein", "0g").replace("g", "").strip()),
                "fat": float(nutrition.get("fat", "0g").replace("g", "").strip())
            }
        except:
            st.session_state.recipe_nutrition[rid] = {
                "calories": float("inf"), "carbs": float("inf"), "protein": float("inf"), "fat": float("inf")
            }

# Sorting logic
sort_key_map = {
    "Calories (low to high)": ("calories", False),
    "Calories (high to low)": ("calories", True),
    "Carbs (low to high)": ("carbs", False),
    "Carbs (high to low)": ("carbs", True),
    "Protein (low to high)": ("protein", False),
    "Protein (high to low)": ("protein", True),
    "Fat (low to high)": ("fat", False),
    "Fat (high to low)": ("fat", True),
}

if sort_option in sort_key_map:
    key, reverse = sort_key_map[sort_option]
    recipes.sort(key=lambda r: st.session_state.recipe_nutrition.get(r["id"], {}).get(key, float("inf")), reverse=reverse)

if not isinstance(recipes, list) or not recipes:
    st.info("No recipes to show.")
else:
    for recipe in recipes:
        st.subheader(recipe.get("title", "Untitled recipe"))
        col1, col2 = st.columns([1, 2])

        with col1:
            for kind in ("usedIngredients", "missedIngredients", "unusedIngredients"):
                items = recipe.get(kind, [])
                if items:
                    label = kind.replace("Ingredients", "")
                    st.markdown(f"**{label} Ingredients**")
                    for ing in items:
                        amt = round(st.session_state.people_count * ing.get("amount", 0), 2)
                        unit = ing.get("unitLong") or ing.get("unit") or ""
                        name = ing.get("originalName") or ing.get("name")
                        st.write(f"- {amt:g} {unit} {name}")
            if recipe not in st.session_state.favorites:
                if st.button("Add to Favorites", key=f"fav_{recipe['id']}"):
                    st.session_state.favorites.append(recipe)
            else:
                if st.button("Remove from Favorites", key=f"rm_{recipe['id']}"):
                    st.session_state.favorites = [
                        r for r in st.session_state.favorites if r["id"] != recipe["id"]
                    ]
                    st.experimental_rerun()

        with col2:
            if recipe.get("image"):
                st.image(
                    recipe["image"],
                    caption=recipe.get("title", ""),
                    use_container_width=True
                )

            combined = recipe.get("usedIngredients", []) + recipe.get("missedIngredients", [])
            data = {
                ing.get("originalName") or ing.get("name"): st.session_state.people_count * ing.get("amount", 0)
                for ing in combined
            }
            df = pd.DataFrame.from_dict(data, orient="index", columns=["Amount"])
            df.index.name = "Ingredient"
            st.bar_chart(df)

            nutrition_data = st.session_state.recipe_nutrition.get(recipe.get("id"), {})
            calories = nutrition_data.get("calories", 0)
            carbs = nutrition_data.get("carbs", 0) * st.session_state.people_count
            protein = nutrition_data.get("protein", 0) * st.session_state.people_count
            fat = nutrition_data.get("fat", 0) * st.session_state.people_count

            macros = {"Carbs": carbs, "Protein": protein, "Fat": fat}
            pie_col, val_col = st.columns([1, 1])

            with pie_col:
                fig, ax = plt.subplots()
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
                st.markdown("**Total:**")
                st.write(f"- Calories: {calories:.0f} kcal")
                st.write(f"- Carbs: {carbs:.1f} g")
                st.write(f"- Protein: {protein:.1f} g")
                st.write(f"- Fat: {fat:.1f} g")
