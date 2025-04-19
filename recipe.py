# Optimierte Version: Recipe Finder

import os
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# API Key aus Umgebungsvariablen
API_KEY = os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

# -------------------- API Funktionen --------------------

def get_recipes(ingredients: str) -> None:
    """Speichert Rezepte basierend auf Zutaten in st.session_state."""
    ingredient_list = [ingredient.strip() for ingredient in ingredients.split(',') if ingredient.strip()]
    ingredients_url_parameters = ',+'.join(ingredient_list)

    response = requests.get(
        f"{API_BASE_URL}/recipes/findByIngredients",
        params={"apiKey": API_KEY, "ingredients": ingredients_url_parameters}
    )

    if response.status_code == 200:
        st.session_state.recipes_data = response.json()
    else:
        st.session_state.recipes_data = []


def get_recipe_information(recipe_id: int) -> dict:
    """Holt vollständige Rezeptdetails."""
    response = requests.get(
        f"{API_BASE_URL}/recipes/{recipe_id}/information",
        params={"apiKey": API_KEY}
    )
    if response.status_code == 200:
        return response.json()
    else:
        return {}


def format_amount_number(amount: float) -> str:
    """Formatiert eine Menge auf zwei Dezimalstellen."""
    amount = round(amount, 2)
    return str(int(amount)) if amount == int(amount) else str(amount)


def create_ingredients_dataframe(people_count: int, recipe: dict) -> pd.DataFrame:
    """Erstellt ein DataFrame der Zutaten."""
    data = {}
    for ingredient in recipe.get("usedIngredients", []) + recipe.get("missedIngredients", []):
        name = ingredient['originalName']
        data[name] = people_count * ingredient['amount']
    df = pd.DataFrame(list(data.items()), columns=['Ingredient', 'Amount'])
    return df


def plot_pie_chart(df: pd.DataFrame, title: str) -> None:
    """Erstellt ein Kreisdiagramm aus einem DataFrame."""
    fig, ax = plt.subplots()
    ax.pie(df['Amount'], labels=df['Ingredient'], autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Kreis statt Oval
    plt.title(title)
    st.pyplot(fig)

# Streamlit App 

# App Konfiguration
st.set_page_config(page_title="Recipe Finder", page_icon="🍽️")

st.title("Recipe Finder")
st.write("""
Discover delicious recipes based on the ingredients you have on hand! 
Simply enter your ingredients and find suitable recipes for your next meal.
""")

# Eingaben
st.subheader("Input Ingredients separated by comma")
people_count = st.number_input("Number of people", min_value=1, max_value=100, step=1, value=1)
ingredients = st.text_input("Ingredients", placeholder="Flour, eggs, ...")

# Initialisiere recipes_data falls nicht vorhanden
if "recipes_data" not in st.session_state:
    st.session_state.recipes_data = []

# Rezepte suchen
st.button("Search Recipes", on_click=get_recipes, args=(ingredients,))

# Ausgabe Rezepte
if st.session_state.recipes_data:
    st.subheader("Recipes")

    for recipe in st.session_state.recipes_data:
        used_ingredients = recipe.get("usedIngredients", [])
        missed_ingredients = recipe.get("missedIngredients", [])
        unused_ingredients = recipe.get("unusedIngredients", [])

        if used_ingredients or missed_ingredients or unused_ingredients:
            st.markdown(f"## {recipe['title']}")

        with st.expander("Show Ingredients"):
            if used_ingredients:
                st.write("### Ingredients used:")
                for ingredient in used_ingredients:
                    amount_str = format_amount_number(people_count * ingredient['amount'])
                    st.write(f"- {amount_str} {ingredient['unitLong']} {ingredient['originalName']}")

            if missed_ingredients:
                st.write("### Missing ingredients:")
                for ingredient in missed_ingredients:
                    amount_str = format_amount_number(people_count * ingredient['amount'])
                    st.write(f"- {amount_str} {ingredient['unitLong']} {ingredient['originalName']}")

            if unused_ingredients:
                st.write("### Ingredients not used:")
                for ingredient in unused_ingredients:
                    amount_str = format_amount_number(people_count * ingredient['amount'])
                    st.write(f"- {amount_str} {ingredient['unitLong']} {ingredient['originalName']}")

        st.image(recipe["image"], caption=recipe["title"], use_column_width=True)

        if st.button(f"Show recipe details", key=f"details_{recipe['id']}"):
            recipe_info = get_recipe_information(recipe['id'])
            if recipe_info:
                st.markdown(f"### Preparation Details")
                st.markdown(f"**Ready in:** {recipe_info.get('readyInMinutes', 'N/A')} minutes")
                st.markdown(f"**Servings:** {recipe_info.get('servings', 'N/A')}")
                st.markdown(f"### Instructions")
                instructions = recipe_info.get('instructions')
                if instructions:
                    steps = instructions.split('.')
                    for idx, step in enumerate(steps):
                        if step.strip():
                            st.write(f"{idx+1}. {step.strip()}.")
                else:
                    st.write("No instructions provided.")

        if st.checkbox(f"Show ingredient chart", key=f"chart_{recipe['id']}"):
            df = create_ingredients_dataframe(people_count, recipe)
            plot_pie_chart(df, recipe['title'])

else:
    st.info("Enter ingredients and click Search Recipes!")

