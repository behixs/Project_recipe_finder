import os
import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
import matplotlib.pyplot as plt

# Read Spoonacular API Key from environment variable
API_KEY = os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

# Helper Functions

def get_recipes(ingredients: str) -> list:
    """Fetch recipes based on provided ingredients."""
    ingredient_list = ingredients.replace(' ', '').split(',')
    ingredients_param = ',+'.join(ingredient_list)
    url = f"{API_BASE_URL}/recipes/findByIngredients"
    params = {"apiKey": API_KEY, "ingredients": ingredients_param, "number": 5}
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()
    else:
        st.error("Error fetching recipes!")
        return []

def get_recipe_information(recipe_id: int) -> dict:
    """Fetch detailed recipe information including nutrition and instructions."""
    url = f"{API_BASE_URL}/recipes/{recipe_id}/information"
    params = {"apiKey": API_KEY, "includeNutrition": True}
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()
    else:
        return {}

def format_amount(amount: float) -> str:
    """Format amount to remove unnecessary decimals."""
    amount = round(amount, 2)
    return str(int(amount)) if amount.is_integer() else str(amount)

def create_ingredients_df(people_count: int, recipe: dict) -> pd.DataFrame:
    """Create a DataFrame for ingredients scaled by people count."""
    data = {}
    for ing in recipe['usedIngredients'] + recipe['missedIngredients']:
        name = ing['originalName']
        amount = ing['amount'] * people_count
        data[name] = amount
    df = pd.DataFrame(list(data.items()), columns=['Ingredient', 'Amount'])
    return df

def save_recipe_pdf(title: str, ingredients: list, summary: str, steps: list, nutrients: dict, filename: str):
    """Save full recipe (ingredients, summary, steps, nutrition) as a PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Recipe: {title}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, summary)
    pdf.ln(5)
    pdf.cell(0, 10, "Ingredients:", ln=True)
    for ing in ingredients:
        pdf.cell(0, 10, f"- {ing}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, "Instructions:", ln=True)
    for idx, step in enumerate(steps, 1):
        pdf.multi_cell(0, 10, f"Step {idx}: {step}")
    pdf.ln(5)
    pdf.cell(0, 10, "Nutrition (per serving):", ln=True)
    pdf.cell(0, 10, f"Calories: {nutrients.get('calories', 'N/A')} kcal", ln=True)
    pdf.cell(0, 10, f"Protein: {nutrients.get('protein', 'N/A')} g", ln=True)
    pdf.cell(0, 10, f"Fat: {nutrients.get('fat', 'N/A')} g", ln=True)
    pdf.cell(0, 10, f"Carbs: {nutrients.get('carbs', 'N/A')} g", ln=True)
    pdf.output(filename)

def save_shopping_list_pdf(title: str, ingredients: list, filename: str):
    """Save only the shopping list as a PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Shopping List for: {title}", ln=True)
    pdf.ln(5)
    for ing in ingredients:
        pdf.cell(0, 10, f"- {ing}", ln=True)
    pdf.output(filename)

def plot_chart(df: pd.DataFrame, chart_type: str):
    """Plot either a bar chart or pie chart of the ingredients."""
    if chart_type == "Bar Chart":
        st.bar_chart(df.set_index('Ingredient'))
    elif chart_type == "Pie Chart":
        fig, ax = plt.subplots()
        ax.pie(df['Amount'], labels=df['Ingredient'], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)

# Streamlit App

st.set_page_config(page_title="Recipe Finder", page_icon="🍝")
st.title("Recipe Finder")
st.write("Enter ingredients to find matching recipes.")

# User inputs
people_count = st.number_input("Number of People", min_value=1, value=1)
ingredients = st.text_input("Ingredients (comma separated)", placeholder="Flour, eggs, milk")
chart_option = st.selectbox("Choose Chart Type", ["Bar Chart", "Pie Chart"])

if st.button("Search Recipes"):
    recipes = get_recipes(ingredients)
    if recipes:
        for recipe in recipes:
            recipe_info = get_recipe_information(recipe['id'])
            if recipe_info:
                st.subheader(recipe_info['title'])
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.image(recipe_info['image'], use_container_width=True)
                    ingredients_list = []
                    for ing in recipe['usedIngredients'] + recipe['missedIngredients']:
                        amount = format_amount(ing['amount'] * people_count)
                        unit = ing.get('unitLong', '')
                        name = ing['originalName']
                        ingredients_list.append(f"{amount} {unit} {name}")
                    st.write("\n".join(ingredients_list))

                    nutrients = {}
                    if 'nutrition' in recipe_info:
                        for nutrient in recipe_info['nutrition']['nutrients']:
                            if 'title' in nutrient:
                                if nutrient['title'] == 'Calories':
                                    nutrients['calories'] = nutrient['amount']
                                elif nutrient['title'] == 'Protein':
                                    nutrients['protein'] = nutrient['amount']
                                elif nutrient['title'] == 'Fat':
                                    nutrients['fat'] = nutrient['amount']
                                elif nutrient['title'] == 'Carbohydrates':
                                    nutrients['carbs'] = nutrient['amount']
                    st.write("**Nutrition:**", nutrients)

                    # Expander for summary and instructions
                    if 'summary' in recipe_info:
                        with st.expander("Recipe Summary"):
                            st.markdown(recipe_info['summary'], unsafe_allow_html=True)

                    steps = []
                    if 'analyzedInstructions' in recipe_info and recipe_info['analyzedInstructions']:
                        for step in recipe_info['analyzedInstructions'][0]['steps']:
                            steps.append(step['step'])

                        with st.expander("Cooking Instructions"):
                            for idx, step in enumerate(steps, 1):
                                st.write(f"{idx}. {step}")

                    # Buttons to generate PDFs
                    if st.button(f"Save Recipe PDF: {recipe_info['title']}"):
                        save_recipe_pdf(recipe_info['title'], ingredients_list, recipe_info.get('summary', ''), steps, nutrients, f"{recipe_info['title']}.pdf")
                        st.success("Recipe PDF saved!")

                    if st.button(f"Create Shopping List PDF: {recipe_info['title']}"):
                        save_shopping_list_pdf(recipe_info['title'], ingredients_list, f"Shopping_List_{recipe_info['title']}.pdf")
                        st.success("Shopping list PDF saved!")

                with col2:
                    df = create_ingredients_df(people_count, recipe)
                    plot_chart(df, chart_option)
