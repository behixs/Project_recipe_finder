import os
import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
import matplotlib.pyplot as plt
from io import BytesIO

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

def create_recipe_pdf(title: str, ingredients: list, summary: str, steps: list, nutrients: dict) -> BytesIO:
    """Create a recipe PDF and return as BytesIO, nicely formatted."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", size=16)
    pdf.cell(0, 10, f"Recipe: {title}", ln=True)
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    
    if summary:
        pdf.set_font("Arial", "B", size=14)
        pdf.cell(0, 10, "Summary:", ln=True)
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, summary)
        pdf.ln(5)
    
    pdf.set_font("Arial", "B", size=14)
    pdf.cell(0, 10, "Ingredients:", ln=True)
    pdf.set_font("Arial", size=12)
    for ing in ingredients:
        pdf.cell(0, 10, f"• {ing}", ln=True)
    pdf.ln(5)
    
    if steps:
        pdf.set_font("Arial", "B", size=14)
        pdf.cell(0, 10, "Instructions:", ln=True)
        pdf.set_font("Arial", size=12)
        for idx, step in enumerate(steps, 1):
            pdf.multi_cell(0, 10, f"Step {idx}: {step}")
        pdf.ln(5)
    
    if nutrients:
        pdf.set_font("Arial", "B", size=14)
        pdf.cell(0, 10, "Nutrition (per serving):", ln=True)
        pdf.set_font("Arial", size=12)
        if nutrients.get('protein'):
            pdf.cell(0, 10, f"Protein: {nutrients['protein']} g", ln=True)
        if nutrients.get('fat'):
            pdf.cell(0, 10, f"Fat: {nutrients['fat']} g", ln=True)
        if nutrients.get('carbs'):
            pdf.cell(0, 10, f"Carbs: {nutrients['carbs']} g", ln=True)
        pdf.ln(5)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return BytesIO(pdf_bytes)

def create_shopping_list_pdf(title: str, ingredients: list) -> BytesIO:
    """Create a shopping list PDF and return as BytesIO, nicely formatted."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", size=16)
    pdf.cell(0, 10, f"Shopping List for: {title}", ln=True)
    
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    for ing in ingredients:
        pdf.cell(0, 10, f"• {ing}", ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    return BytesIO(pdf_bytes)

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
st.title("🍝 Recipe Finder")
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
                                if nutrient['title'] == 'Protein':
                                    nutrients['protein'] = nutrient['amount']
                                elif nutrient['title'] == 'Fat':
                                    nutrients['fat'] = nutrient['amount']
                                elif nutrient['title'] == 'Carbohydrates':
                                    nutrients['carbs'] = nutrient['amount']
                    st.write("**Nutrition:**", nutrients)

                    # Expanders for summary and steps
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

                    # Clean filename
                    safe_title = recipe_info['title'].replace(' ', '_').replace('/', '_')

                    # Download buttons
                    recipe_pdf = create_recipe_pdf(recipe_info['title'], ingredients_list, recipe_info.get('summary', ''), steps, nutrients)
                    st.download_button(
                        label="Download Recipe PDF",
                        data=recipe_pdf,
                        file_name=f"{safe_title}.pdf",
                        mime="application/pdf"
                    )

                    shopping_list_pdf = create_shopping_list_pdf(recipe_info['title'], ingredients_list)
                    st.download_button(
                        label="Download Shopping List PDF",
                        data=shopping_list_pdf,
                        file_name=f"Shopping_List_{safe_title}.pdf",
                        mime="application/pdf"
                    )

                with col2:
                    df = create_ingredients_df(people_count, recipe)
                    plot_chart(df, chart_option)

