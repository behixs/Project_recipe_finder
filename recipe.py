# Import required packages
import os
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# Get API Key from Streamlit Secrets (for Streamlit Cloud) or environment variable (for local)
API_KEY = st.secrets["API_KEY"] if "API_KEY" in st.secrets else os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

# Initialize session state for recipes and favorites
if "recipes_data" not in st.session_state:
    st.session_state.recipes_data = []
if "favorites" not in st.session_state:
    st.session_state.favorites = []

def get_recipes(ingredients: str) -> None:
    """Fetch recipes from Spoonacular API and save them in session state."""
    ingredient_list = [i.strip() for i in ingredients.split(',') if i.strip()]
    ingredients_url_parameters = ',+'.join(ingredient_list)
    response = requests.get(
        f"{API_BASE_URL}/recipes/findByIngredients",
        params={"apiKey": API_KEY, "ingredients": ingredients_url_parameters}
    )
    if response.status_code == 200:
        st.session_state.recipes_data = response.json()
    else:
        st.session_state.recipes_data = []
        st.error("Something went wrong. Please check your API key or try again later.")

def format_amount_number(amount: float) -> str:
    """Round a number to two decimal places and return it as a string."""
    amount = round(amount, 2)
    return str(int(amount)) if amount == int(amount) else str(amount)

def create_ingredients_dataframe(people_count: int, recipe: dict) -> pd.DataFrame:
    """Create a DataFrame with ingredient amounts adjusted for the number of people."""
    data = {}
    for ingredient in recipe.get("usedIngredients", []):
        name = ingredient['originalName']
        data[name] = people_count * ingredient['amount']
    for ingredient in recipe.get("missedIngredients", []):
        name = ingredient['originalName']
        data[name] = people_count * ingredient['amount']
    df = pd.DataFrame.from_dict(data, orient='index', columns=['Amount'])
    df.index.name = 'Ingredient'
    return df

# App layout
st.set_page_config(page_title="Recipe Finder", page_icon="🥗", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: white;
        }
        .stApp {
            background-color: #0e1117;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Recipe Finder")
st.write("""
Discover delicious recipes based on the ingredients you have on hand!  
Simply enter your ingredients and find suitable recipes for your next meal.
""")

# User input
st.subheader("Input Ingredients separated by comma")
people_count = st.number_input("Number of people", min_value=1, max_value=100, step=1, value=1)
ingredients = st.text_input("Ingredients", placeholder="Flour, eggs, ...")
st.button("Search Recipes", on_click=get_recipes, args=(ingredients,))

# Display favorites
if st.session_state.favorites:
    st.subheader("⭐ Favorite Recipes")
    for fav in st.session_state.favorites:
        st.markdown(f"- {fav}")

# Display recipe results
if st.session_state.recipes_data:
    st.subheader("Recipes")

    for recipe in st.session_state.recipes_data:
        used_ingredients = recipe.get("usedIngredients", [])
        missed_ingredients = recipe.get("missedIngredients", [])
        unused_ingredients = recipe.get("unusedIngredients", [])

        with st.container():
            st.markdown(f"## {recipe['title']}")
            cols = st.columns([1, 2])

            with cols[0]:
                # Show recipe image
                st.image(recipe.get("image", "https://via.placeholder.com/150"), use_container_width=True)
                # Favorite button
                if st.button(f"❤️ Add to favorites: {recipe['title']}"):
                    if recipe['title'] not in st.session_state.favorites:
                        st.session_state.favorites.append(recipe['title'])
                        st.success(f"Added '{recipe['title']}' to favorites")

            with cols[1]:
                # Show used ingredients as tags
                st.markdown("**Ingredients used:**")
                for ing in used_ingredients:
                    st.markdown(f"<span style='background-color:#2a9d8f;padding:4px 8px;border-radius:12px;margin:2px;display:inline-block;'>{format_amount_number(people_count * ing['amount'])} {ing['unit']} {ing['originalName']}</span>", unsafe_allow_html=True)

                # Show missing ingredients as bullet list
                st.markdown("**Missing ingredients:**")
                for ing in missed_ingredients:
                    st.markdown(f"- {format_amount_number(people_count * ing['amount'])} {ing['unit']} {ing['originalName']}")

                # Show unused ingredients as bullet list
                if unused_ingredients:
                    st.markdown("**Ingredients not used:**")
                    for ing in unused_ingredients:
                        st.markdown(f"- {format_amount_number(people_count * ing['amount'])} {ing['unit']} {ing['originalName']}")

                # Show pie chart
                df = create_ingredients_dataframe(people_count, recipe)
                if not df.empty:
                    fig, ax = plt.subplots()
                    ax.pie(df['Amount'], labels=df.index, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    st.pyplot(fig)

# Generate shopping list from all missing ingredients
all_missing = [i['originalName'] for r in st.session_state.recipes_data for i in r.get("missedIngredients", [])]
if all_missing:
    st.subheader("🛒 Shopping List")
    for item in sorted(set(all_missing)):
        st.checkbox(item, key=f"chk_{item}")

