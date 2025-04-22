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
    """Create a nicely formatted recipe PDF and return as BytesIO."""
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
        pdf.cell(0, 10, "Nutrition

