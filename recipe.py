import os
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# API Key
API_KEY = os.getenv("API_KEY")
API_BASE_URL = "https://api.spoonacular.com"

# -------------------- Funktionen --------------------

def get_recipes(ingredients: str, sort_by: str = "popularity") -> list:
    """Holt Rezepte basierend auf Zutaten."""
    ingredient_list = [ingredient.strip() for ingredient in ingredients.split(',') if ingredient.strip()]
    params = {
        "apiKey": API_KEY,
        "ingredients": ',+'.join(ingredient_list),
        "number": 10,
        "ranking": 1 if sort_by == "popularity" else 2
    }
    response = requests.get(f"{API_BASE_URL}/recipes/findByIngredients", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch recipes. Please check your API Key or ingredients.")
        return []

def get_recipe_details(recipe_id: int) -> dict:
    """Holt vollständige Details zu einem Rezept."""
    params = {"apiKey": API_KEY}
    response = requests.get(f"{API_BASE_URL}/recipes/{recipe_id}/information", params=params)
    if response.status_code == 200:
        return response.json()
    return {}

def format_amount(amount: float) -> str:
    """Formatiert eine Zahl schön."""
    amount = round(amount, 2)
    return str(int(amount)) if amount == int(amount) else str(amount)

def create_ingredients_dataframe(recipe: dict, people: int) -> pd.DataFrame:
    """Erstellt Zutaten-DataFrame."""
    ingredients = {}
    for ingredient in recipe.get("usedIngredients", []) + recipe.get("missedIngredients", []):
        name = ingredient["originalName"]
        ingredients[name] = people * ingredient["amount"]
    df = pd.DataFrame(list(ingredients.items()), columns=["Ingredient", "Amount"])
    return df

def plot_pie_chart(df: pd.DataFrame, title: str):
    """Zeichnet ein Kreisdiagramm."""
    df_sorted = df.sort_values("Amount", ascending=False)
    if len(df_sorted) > 5:
        top = df_sorted.iloc[:4]
        others = pd.DataFrame([["Other", df_sorted.iloc[4:]["Amount"].sum()]], columns=["Ingredient", "Amount"])
        df_sorted = pd.concat([top, others])
    fig, ax = plt.subplots()
    ax.pie(df_sorted['Amount'], labels=df_sorted['Ingredient'], autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

def generate_pdf(recipe_info: dict):
    """Erstellt ein PDF des Rezepts."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Titel
    pdf.cell(0, 10, recipe_info['title'], ln=True, align='C')
    pdf.ln(10)
    
    # Details
    pdf.cell(0, 10, f"Ready in {recipe_info.get('readyInMinutes', 'N/A')} minutes", ln=True)
    pdf.cell(0, 10, f"Servings: {recipe_info.get('servings', 'N/A')}", ln=True)
    pdf.ln(10)
    
    # Zutatenliste
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 10, "Ingredients:", ln=True)
    pdf.set_font("Arial", size=11)
    for ing in recipe_info.get('extendedIngredients', []):
        pdf.cell(0, 10, f"- {ing['originalString']}", ln=True)
    
    pdf.ln(10)
    
    # Anleitung
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 10, "Instructions:", ln=True)
    pdf.set_font("Arial", size=11)
    instructions = recipe_info.get('instructions')
    if instructions:
        steps = instructions.split('.')
        for idx, step in enumerate(steps):
            if step.strip():
                pdf.multi_cell(0, 10, f"{idx+1}. {step.strip()}")
    else:
        pdf.cell(0, 10, "No instructions provided.", ln=True)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)
    return temp_file.name

# -------------------- Streamlit App --------------------

st.set_page_config(page_title="Recipe Finder", page_icon="🍽️")

st.title("🍽️ Recipe Finder Premium")
st.write("Find perfect recipes with your available ingredients!")

# Eingaben
with st.sidebar:
    st.header("Settings")
    people = st.number_input("Number of People", min_value=1, value=1)
    ingredients = st.text_input("Ingredients (comma separated)", placeholder="Flour, eggs, cheese...")
    sort_by = st.radio("Sort recipes by:", ["popularity", "minimize missing ingredients"])
    search = st.button("🔍 Search Recipes")

recipes = []

if search:
    if ingredients:
        recipes = get_recipes(ingredients, sort_by)
    else:
        st.warning("Please enter some ingredients first.")

# Anzeige der Rezepte
if recipes:
    for recipe in recipes:
        with st.container():
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(recipe["title"])
                used = [f"{ing['originalName']} ({format_amount(ing['amount'])} {ing['unitLong']})" for ing in recipe.get('usedIngredients', [])]
                missed = [f"{ing['originalName']} ({format_amount(ing['amount'])} {ing['unitLong']})" for ing in recipe.get('missedIngredients', [])]

                with st.expander("🛒 Ingredients"):
                    if used:
                        st.markdown("**Used Ingredients:**")
                        st.write(", ".join(used))
                    if missed:
                        st.markdown("**Missing Ingredients:**")
                        st.write(", ".join(missed))

            with col2:
                st.image(recipe["image"], use_container_width=True)

            with st.expander("📋 Recipe Details"):
                details = get_recipe_details(recipe['id'])
                if details:
                    st.markdown(f"**Ready in:** {details.get('readyInMinutes', 'N/A')} minutes")
                    st.markdown(f"**Servings:** {details.get('servings', 'N/A')}")
                    instructions = details.get('instructions', '')
                    if instructions:
                        steps = instructions.split('.')
                        for idx, step in enumerate(steps):
                            if step.strip():
                                st.write(f"{idx+1}. {step.strip()}.")

                    if st.button(f"⬇️ Download {recipe['title']} as PDF", key=f"pdf_{recipe['id']}"):
                        file_path = generate_pdf(details)
                        with open(file_path, "rb") as f:
                            st.download_button(label="Download PDF", data=f, file_name=f"{recipe['title']}.pdf", mime="application/pdf")

            st.divider()

            if st.checkbox(f"Show Ingredients Chart for {recipe['title']}", key=f"chart_{recipe['id']}"):
                df = create_ingredients_dataframe(recipe, people)
                plot_pie_chart(df, recipe['title'])

else:
    if search:
        st.info("No recipes found. Try adjusting your ingredients or settings.")

