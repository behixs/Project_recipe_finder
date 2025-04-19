import os
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# API
API_KEY = os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

# Funktionen
def get_recipes(ingredients: str, sort_by: str = "popularity") -> list:
    ingredient_list = [ingredient.strip() for ingredient in ingredients.split(',') if ingredient.strip()]
    params = {
        "apiKey": API_KEY,
        "ingredients": ',+'.join(ingredient_list),
        "number": 10,
        "ranking": 1 if sort_by == "popularity" else 2
    }
    response = requests.get(f"{API_BASE_URL}/recipes/findByIngredients", params=params)
    return response.json() if response.status_code == 200 else []

def get_recipe_details(recipe_id: int) -> dict:
    params = {"apiKey": API_KEY}
    response = requests.get(f"{API_BASE_URL}/recipes/{recipe_id}/information", params=params)
    return response.json() if response.status_code == 200 else {}

def format_amount(amount: float) -> str:
    amount = round(amount, 2)
    return str(int(amount)) if amount == int(amount) else str(amount)

def create_ingredients_dataframe(recipe: dict, people: int) -> pd.DataFrame:
    ingredients = {}
    for ingredient in recipe.get("usedIngredients", []) + recipe.get("missedIngredients", []):
        name = ingredient["originalName"]
        ingredients[name] = people * ingredient["amount"]
    df = pd.DataFrame(list(ingredients.items()), columns=["Ingredient", "Amount"])
    return df

def plot_pie_chart(df: pd.DataFrame, title: str):
    df_sorted = df.sort_values("Amount", ascending=False)
    if len(df_sorted) > 5:
        top = df_sorted.iloc[:4]
        others = pd.DataFrame([["Other", df_sorted.iloc[4:]["Amount"].sum()]], columns=["Ingredient", "Amount"])
        df_sorted = pd.concat([top, others])
    fig, ax = plt.subplots()
    ax.pie(df_sorted['Amount'], labels=df_sorted['Ingredient'], autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig, use_container_width=True)

def extract_instructions(details: dict) -> list:
    """Nimmt saubere Kochschritte aus analyzedInstructions."""
    steps = []
    if details.get('analyzedInstructions'):
        for step in details['analyzedInstructions'][0]['steps']:
            steps.append(step['step'])
    return steps

# Streamlit App
st.set_page_config(page_title="Recipe Finder Premium", page_icon="")

st.title("Recipe Finder Premium")
st.write("Find perfect recipes based on your available ingredients.")

# Sidebar Eingaben
with st.sidebar:
    st.header("Settings")
    people = st.number_input("Number of People", min_value=1, value=1)
    ingredients = st.text_input("Ingredients (comma separated)", placeholder="Flour, eggs, cheese...")
    sort_by = st.radio("Sort recipes by:", ["popularity", "minimize missing ingredients"])
    search = st.button("Search Recipes")

recipes = []

if search and ingredients:
    recipes = get_recipes(ingredients, sort_by)

# Ausgabe
if recipes:
    for recipe in recipes:
        with st.container():
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(recipe["title"])
                used = [f"{ing['originalName']} ({format_amount(ing['amount'])} {ing['unitLong']})" for ing in recipe.get('usedIngredients', [])]
                missed = [f"{ing['originalName']} ({format_amount(ing['amount'])} {ing['unitLong']})" for ing in recipe.get('missedIngredients', [])]

                with st.expander("Ingredients"):
                    if used:
                        st.markdown("**Used Ingredients:**")
                        st.write(", ".join(used))
                    if missed:
                        st.markdown("**Missing Ingredients:**")
                        st.write(", ".join(missed))

            with col2:
                st.image(recipe["image"], use_container_width=True)

            with st.expander("Recipe Details"):
                details = get_recipe_details(recipe['id'])
                if details:
                    st.markdown(f"**Ready in:** {details.get('readyInMinutes', 'N/A')} minutes")
                    st.markdown(f"**Servings:** {details.get('servings', 'N/A')}")

                    instructions = extract_instructions(details)
                    if instructions:
                        for idx, step in enumerate(instructions):
                            st.write(f"{idx+1}. {step}")
                    else:
                        st.write("No detailed instructions provided.")

            st.divider()

            if st.checkbox(f"Show Ingredients Chart for {recipe['title']}", key=f"chart_{recipe['id']}"):
                df = create_ingredients_dataframe(recipe, people)
                plot_pie_chart(df, recipe['title'])

else:
    if search:
        st.warning("No recipes found. Try different ingredients.")
