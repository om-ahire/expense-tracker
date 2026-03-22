from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kharchameter_secret_key"

USERS_FILE = "users.csv"
EXPENSES_FILE = "expenses.csv"

# ---------------- FILE SETUP ----------------
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["Username", "Password"]).to_csv(USERS_FILE, index=False)

if not os.path.exists(EXPENSES_FILE):
    pd.DataFrame(
        columns=["Username", "Date", "Amount", "Category", "Description"]
    ).to_csv(EXPENSES_FILE, index=False)

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = session["username"]
    df = pd.read_csv(EXPENSES_FILE)
    user_df = df[df["Username"] == user]

    total_expenses = float(user_df["Amount"].sum()) if not user_df.empty else 0

    # Calculate monthly_expenses
    monthly_expenses = 0
    if not user_df.empty:
        user_df["Date"] = pd.to_datetime(user_df["Date"])
        current_month = datetime.now().month
        current_year = datetime.now().year
        monthly_df = user_df[(user_df["Date"].dt.month == current_month) & (user_df["Date"].dt.year == current_year)]
        monthly_expenses = float(monthly_df["Amount"].sum())
        user_df["Date"] = user_df["Date"].dt.strftime("%Y-%m-%d")

    # ---------- LINE CHART (date-wise) ----------
    if not user_df.empty:
        daily = user_df.groupby("Date")["Amount"].sum().reset_index()
        line_labels = daily["Date"].tolist()
        line_values = daily["Amount"].tolist()
    else:
        line_labels, line_values = [], []

    # ---------- PIE CHART (category-wise) ----------
    if not user_df.empty:
        category_data = user_df.groupby("Category")["Amount"].sum().to_dict()
    else:
        category_data = {}

    top_category = max(category_data, key=category_data.get) if category_data else "None"

    # ---------- AI INSIGHTS ----------
    predicted_budget = round(total_expenses * 1.2, 2)
    spending_trend = "Increasing" if total_expenses > 5000 else "Stable"
    avg_daily = total_expenses / 30 if total_expenses > 0 else 0

    ai_insights = {
        "spending_trend": spending_trend,
        "avg_daily": avg_daily,
        "top_category": top_category,
        "recommendations": [
            f"You spent ₹{int(monthly_expenses)} this month.",
            f"Biggest expense category: {top_category}.",
            "Try setting a weekly spending limit and avoid impulse purchases."
        ]
    }
    
    recent_expenses = user_df.tail(6).reset_index().to_dict("records")

    return render_template(
        "index.html",
        total_expenses=total_expenses,
        monthly_expenses=monthly_expenses,
        predicted_budget=predicted_budget,
        category_data=category_data,
        recent_expenses=recent_expenses,
        current_date=datetime.now().strftime("%Y-%m-%d"),
        ai_insights=ai_insights,
        username=user
    )

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "username" not in session:
        return redirect(url_for("login"))

    df = pd.read_csv(EXPENSES_FILE)
    df.loc[len(df)] = [
        session["username"],
        request.form["date"],
        float(request.form["amount"]),
        request.form["category"],
        request.form["description"]
    ]
    df.to_csv(EXPENSES_FILE, index=False)

    return redirect(url_for("home"))

@app.route("/ai_chat", methods=["POST"])
def ai_chat():
    msg = request.json.get("message", "").lower()
    if "save" in msg:
        return jsonify({"response": "Cut down on food delivery and impulse buys."})
    if "category" in msg:
        return jsonify({"response": "Your top spending category is Food."})
    return jsonify({"response": "Ask me about savings or spending patterns."})

@app.route("/delete_expense/<int:expense_index>", methods=["POST"])
def delete_expense(expense_index):
    if "username" not in session:
        return redirect(url_for("login"))
    
    user = session["username"]
    df = pd.read_csv(EXPENSES_FILE)
    
    if expense_index in df.index and df.loc[expense_index, "Username"] == user:
        df = df.drop(index=expense_index)
        df.to_csv(EXPENSES_FILE, index=False)
        
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = pd.read_csv(USERS_FILE)
        u, p = request.form["username"], request.form["password"]

        if u in users["Username"].values:
            stored = str(users.loc[users["Username"] == u, "Password"].values[0])
            
            # Check if it's a valid hash
            try:
                is_valid = check_password_hash(stored, p)
            except ValueError:
                is_valid = False
                
            if is_valid:
                session["username"] = u
                return redirect(url_for("home"))
            elif stored == p:
                # Migrate older plain text passwords to hash
                users.loc[users["Username"] == u, "Password"] = generate_password_hash(p)
                users.to_csv(USERS_FILE, index=False)
                session["username"] = u
                return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users = pd.read_csv(USERS_FILE)
        u, p = request.form["username"], request.form["password"]
        if u in users["Username"].values:
            return render_template("register.html", error="User exists")

        users.loc[len(users)] = [u, generate_password_hash(p)]
        users.to_csv(USERS_FILE, index=False)
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
