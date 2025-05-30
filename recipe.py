import requests
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ——— Konfiguration ———
API_KEY = "38383701bda9437486582fa552663a1a"  # 🔴 HIER DEINEN SPOONACULAR API-KEY EINFÜGEN
API_BASE_URL = "https://api.spoonacular.com"

st.set_page_config(page_title="Recipe Finder", page_icon="🍽️")
st.title("🍽️ Recipe Finder")
st.write("Entdecke köstliche Rezepte basierend auf deinen vorhandenen Zutaten!")

# ——— Fehler bei fehlendem Key ———
if not API_KEY or API_KEY == "DEIN_API_KEY_HIER_EINFÜGEN":
    st.error("❌ Kein gültiger API-Key. Bitte ersetze `API_KEY` oben im Code durch deinen Spoonacular API-Key.")
    st.stop()

# ——— Session State Initialization ———
if "recipes_data" not in st.session_state:
    st.session_state.recipes_data = []

# ——— Eingabe ———
people_count = st.number_input(
    "Anzahl der Personen",
    min_value=1,
    max_value=100,
    value=1,
    step=1,
    key="people_count",
)

ingredients = st.text_input(
    "Zutaten (kommagetrennt)",
    key="ingredients",
    placeholder="z. B. mehl, eier, milch",
)

# ——— Daten holen ———
def fetch_recipes(ingredients_str: str):
    params = {
        "apiKey": API_KEY,
        "ingredients": ingredients_str,
        "number": 5,
        "ranking": 1,
    }
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

# ——— Rezeptsuche ———
if st.button("🔍 Rezepte suchen"):
    ingr = ingredients.strip()
    if not ingr:
        st.warning("❗ Bitte gib mindestens eine Zutat ein.")
    else:
        try:
            st.session_state.recipes_data = fetch_recipes(ingr)
        except requests.HTTPError as e:
            st.error(f"API Fehler: {e}")
            st.session_state.recipes_data = []

# ——— Ergebnisse anzeigen ———
recipes = st.session_state.recipes_data

if not isinstance(recipes, list) or not recipes:
    st.info("ℹ️ Keine Rezepte gefunden. Versuche es mit anderen Zutaten.")
else:
    for recipe in recipes:
        st.subheader(recipe.get("title", "Unbenanntes Rezept"))
        col1, col2 = st.columns([1, 2])

        with col1:
            for kind in ("usedIngredients", "missedIngredients", "unusedIngredients"):
                items = recipe.get(kind, [])
                if items:
                    label = kind.replace("Ingredients", "")
                    st.markdown(f"**{label.capitalize()} Zutaten**")
                    for ing in items:
                        amt = round(people_count * ing.get("amount", 0), 2)
                        unit = ing.get("unitLong") or ing.get("unit") or ""
                        name = ing.get("originalName") or ing.get("name")
                        st.write(f"- {amt:g} {unit} {name}")

        with col2:
            if recipe.get("image"):
                st.image(recipe["image"], caption=recipe.get("title", ""), use_container_width=True)

            combined = recipe.get("usedIngredients", []) + recipe.get("missedIngredients", [])
            data = {
                ing.get("originalName") or ing.get("name"): people_count * ing.get("amount", 0)
                for ing in combined
            }
            df = pd.DataFrame.from_dict(data, orient="index", columns=["Menge"])
            df.index.name = "Zutat"
            st.bar_chart(df)

            try:
                nutrition = fetch_nutrition(recipe.get("id"))
                carbs = float(nutrition.get("carbs", "0g").rstrip("g")) * people_count
                protein = float(nutrition.get("protein", "0g").rstrip("g")) * people_count
                fat = float(nutrition.get("fat", "0g").rstrip("g")) * people_count

                macros = {"Kohlenhydrate": carbs, "Eiweiß": protein, "Fett": fat}
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
                    ax.set_title("Makronährstoffverteilung")
                    ax.axis("equal")
                    st.pyplot(fig)

                with val_col:
                    st.markdown("**Gesamt (pro Tag, in Gramm):**")
                    st.write(f"- Kohlenhydrate: {carbs:.1f} g")
                    st.write(f"- Eiweiß: {protein:.1f} g")
                    st.write(f"- Fett: {fat:.1f} g")

            except requests.HTTPError:
                st.warning("⚠️ Nährwertdaten konnten nicht geladen werden.")
