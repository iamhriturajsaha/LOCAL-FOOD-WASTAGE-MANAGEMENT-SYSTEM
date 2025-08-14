import streamlit as st
import pandas as pd
import sqlite3

# =========================
# DATABASE CONNECTION
# =========================
DB_PATH = "Food Wastage.db"

def run_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(query, conn, params=params)

def execute_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_table_columns(table_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

# =========================
# APP TITLE
# =========================
st.set_page_config(page_title="Food Wastage Insights Dashboard", layout="wide")
st.title("🍽 Food Wastage Insights Dashboard")

# =========================
# FILTERS
# =========================
st.sidebar.header("🔍 Filters")
location_filter = st.sidebar.text_input("Filter by City")
provider_filter = st.sidebar.text_input("Filter by Provider Name")
food_type_filter = st.sidebar.text_input("Filter by Food Type")
provider_type_filter = st.sidebar.text_input("Filter by Provider Type")

# Check provider table columns
provider_columns = get_table_columns("providers")

# =========================
# SQL QUERIES
# =========================
queries = {
    "Providers & Receivers by City": '''
        SELECT p.City,
               COUNT(DISTINCT p.Provider_ID) AS Providers,
               COUNT(DISTINCT r.Receiver_ID) AS Receivers
        FROM providers p
        LEFT JOIN receivers r ON p.City = r.City
        GROUP BY p.City;
    ''',
    "Top Food Provider Type": '''
        SELECT Provider_Type, SUM(Quantity) AS Total_Food
        FROM providers p
        JOIN food_listings f ON p.Provider_ID = f.Provider_ID
        GROUP BY Provider_Type
        ORDER BY Total_Food DESC;
    ''' if "Provider_Type" in provider_columns else None,
    "Provider Contact by City": '''
        SELECT Name, Contact, City
        FROM providers
        WHERE City LIKE ?;
    ''',
    "Top Receivers by Claims": '''
        SELECT r.Name, COUNT(c.Claim_ID) AS Total_Claims
        FROM receivers r
        JOIN claims c ON r.Receiver_ID = c.Receiver_ID
        GROUP BY r.Name
        ORDER BY Total_Claims DESC;
    ''',
    "Total Quantity Available": '''
        SELECT SUM(Quantity) AS Total_Available
        FROM food_listings;
    ''',
    "City with Most Listings": '''
        SELECT Location, COUNT(*) AS Listing_Count
        FROM food_listings
        GROUP BY Location
        ORDER BY Listing_Count DESC
        LIMIT 1;
    ''',
    "Most Common Food Types": '''
        SELECT Food_Type, COUNT(*) AS Count
        FROM food_listings
        GROUP BY Food_Type
        ORDER BY Count DESC;
    ''',
    "Claims per Food Item": '''
        SELECT f.Food_Type, COUNT(c.Claim_ID) AS Claims
        FROM claims c
        JOIN food_listings f ON c.Food_ID = f.Food_ID
        GROUP BY f.Food_Type;
    ''',
    "Provider with Most Successful Claims": '''
        SELECT p.Name, COUNT(c.Claim_ID) AS Successful_Claims
        FROM providers p
        JOIN food_listings f ON p.Provider_ID = f.Provider_ID
        JOIN claims c ON f.Food_ID = c.Food_ID
        WHERE c.Status = 'Completed'
        GROUP BY p.Name
        ORDER BY Successful_Claims DESC
        LIMIT 1;
    ''',
    "Claim Status Percentages": '''
        SELECT Status,
               ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM claims)), 2) AS Percentage
        FROM claims
        GROUP BY Status;
    ''',
    "Avg Quantity Claimed per Receiver": '''
        SELECT r.Name, ROUND(AVG(f.Quantity), 2) AS Avg_Quantity
        FROM receivers r
        JOIN claims c ON r.Receiver_ID = c.Receiver_ID
        JOIN food_listings f ON c.Food_ID = f.Food_ID
        GROUP BY r.Name;
    ''',
    "Most Claimed Meal Type": '''
        SELECT Meal_Type, COUNT(*) AS Claims
        FROM food_listings f
        JOIN claims c ON f.Food_ID = c.Food_ID
        GROUP BY Meal_Type
        ORDER BY Claims DESC
        LIMIT 1;
    ''',
    "Total Quantity by Provider": '''
        SELECT p.Name, SUM(f.Quantity) AS Total_Donated
        FROM providers p
        JOIN food_listings f ON p.Provider_ID = f.Provider_ID
        GROUP BY p.Name;
    '''
}

# =========================
# DISPLAY RESULTS
# =========================
st.header("📊 SQL Insights")

for title, sql in queries.items():
    if sql:
        st.subheader(title)
        if "Provider Contact by City" in title:
            df = run_query(sql, (f"%{location_filter}%",))
        else:
            df = run_query(sql)
        st.dataframe(df)

# =========================
# PROVIDER CONTACT DETAILS
# =========================
st.header("📞 Contact Food Providers Directly")

contact_query = "SELECT Name, City, Contact" + (", Provider_Type" if "Provider_Type" in provider_columns else "") + " FROM providers WHERE 1=1"
params = []

if location_filter:
    contact_query += " AND City LIKE ?"
    params.append(f"%{location_filter}%")
if provider_type_filter and "Provider_Type" in provider_columns:
    contact_query += " AND Provider_Type LIKE ?"
    params.append(f"%{provider_type_filter}%")
if provider_filter:
    contact_query += " AND Name LIKE ?"
    params.append(f"%{provider_filter}%")

contact_df = run_query(contact_query, tuple(params))
st.dataframe(contact_df)

# =========================
# CRUD OPERATIONS
# =========================
st.header("🛠 Manage Records")

crud_action = st.selectbox("Select Action", ["Add Provider", "Update Provider", "Delete Provider"])

if crud_action == "Add Provider":
    name = st.text_input("Name")
    city = st.text_input("City")
    contact = st.text_input("Contact")
    provider_type = st.text_input("Provider Type") if "Provider_Type" in provider_columns else None
    if st.button("Add"):
        if "Provider_Type" in provider_columns:
            execute_query(
                "INSERT INTO providers (Name, City, Provider_Type, Contact) VALUES (?, ?, ?, ?)",
                (name, city, provider_type, contact)
            )
        else:
            execute_query(
                "INSERT INTO providers (Name, City, Contact) VALUES (?, ?, ?)",
                (name, city, contact)
            )
        st.success("Provider added successfully!")

elif crud_action == "Update Provider":
    provider_id = st.number_input("Provider ID", step=1)
    contact = st.text_input("New Contact")
    if st.button("Update"):
        execute_query(
            "UPDATE providers SET Contact = ? WHERE Provider_ID = ?",
            (contact, provider_id)
        )
        st.success("Provider updated successfully!")

elif crud_action == "Delete Provider":
    provider_id = st.number_input("Provider ID", step=1)
    if st.button("Delete"):
        execute_query("DELETE FROM providers WHERE Provider_ID = ?", (provider_id,))
        st.success("Provider deleted successfully!")
