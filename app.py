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

# ---------------- HELPER FOR DASHBOARD DATA ----------------
def get_dashboard_data(user):
    user_lc = user.strip().lower()
    if not os.path.exists(EXPENSES_FILE):
        pd.DataFrame(columns=["Username", "Date", "Amount", "Category", "Description"]).to_csv(EXPENSES_FILE, index=False)
        
    df = pd.read_csv(EXPENSES_FILE, dtype={"Username": str, "Category": str, "Description": str})
    df["Username"] = df["Username"].fillna("").str.strip().str.lower()
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0.0)
    
    user_df = df[df["Username"] == user_lc]

    total_expenses = float(user_df["Amount"].sum()) if not user_df.empty else 0.0

    # Calculate monthly_expenses
    monthly_expenses = 0.0
    if not user_df.empty:
        user_df = user_df.copy()
        user_df["Date"] = pd.to_datetime(user_df["Date"], errors='coerce')
        user_df["Date"] = user_df["Date"].fillna(pd.Timestamp(datetime.now().strftime("%Y-%m-%d")))
        current_month = datetime.now().month
        current_year = datetime.now().year
        monthly_df = user_df[(user_df["Date"].dt.month == current_month) & (user_df["Date"].dt.year == current_year)]
        monthly_expenses = float(monthly_df["Amount"].sum())
        user_df["Date"] = user_df["Date"].dt.strftime("%Y-%m-%d")

    # ---------- PIE CHART (category-wise) ----------
    if not user_df.empty:
        category_data = user_df.groupby("Category")["Amount"].sum().to_dict()
    else:
        category_data = {}

    top_category = max(category_data, key=category_data.get) if category_data else "None"

    # ---------- AI INSIGHTS ----------
    predicted_budget = round(total_expenses * 1.2, 2)
    spending_trend = "Increasing" if total_expenses > 5000 else "Stable"
    avg_daily = round(total_expenses / 30, 2) if total_expenses > 0 else 0.0

    # Standardize categories mapping for breakdown colors
    standard_categories = ["Food", "Transportation", "Entertainment", "Shopping", "Bills", "Healthcare", "Travel", "Other"]
    for cat in category_data.copy():
        if cat not in standard_categories and cat:
            category_data[cat] = float(category_data[cat])

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
    
    recent_expenses = user_df.tail(10).reset_index().to_dict("records")
    for exp in recent_expenses:
        if 'index' in exp:
            exp['index'] = int(exp['index'])
        if 'Amount' in exp:
            exp['Amount'] = float(exp['Amount'])
        if 'Description' in exp:
            exp['Description'] = str(exp['Description']).replace('\n', ' ').strip()
            
    # Reverse recent expenses to show newer items first
    recent_expenses = list(reversed(recent_expenses))

    return {
        "total_expenses": total_expenses,
        "monthly_expenses": monthly_expenses,
        "predicted_budget": predicted_budget,
        "category_data": category_data,
        "recent_expenses": recent_expenses,
        "ai_insights": ai_insights
    }

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = session["username"]
    data = get_dashboard_data(user)

    return render_template(
        "index.html",
        total_expenses=data["total_expenses"],
        monthly_expenses=data["monthly_expenses"],
        predicted_budget=data["predicted_budget"],
        category_data=data["category_data"],
        recent_expenses=data["recent_expenses"],
        current_date=datetime.now().strftime("%Y-%m-%d"),
        ai_insights=data["ai_insights"],
        username=user
    )

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "username" not in session:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        return redirect(url_for("login"))

    if request.is_json:
        req_data = request.json
        date_val = req_data.get("date")
        amount_val = float(req_data.get("amount", 0))
        category_val = req_data.get("category")
        description_val = req_data.get("description", "")
    else:
        date_val = request.form.get("date")
        amount_val = float(request.form.get("amount", 0))
        category_val = request.form.get("category")
        description_val = request.form.get("description", "")

    user = session["username"].strip().lower()
    df = pd.read_csv(EXPENSES_FILE, dtype={"Username": str, "Category": str, "Description": str})
    
    new_expense = pd.DataFrame([[user, date_val, amount_val, category_val, description_val]], 
                               columns=["Username", "Date", "Amount", "Category", "Description"])
    df = pd.concat([df, new_expense], ignore_index=True)
    df.to_csv(EXPENSES_FILE, index=False)

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.form.get("ajax") == "true" or request.args.get("ajax") == "true":
        data = get_dashboard_data(user)
        data["success"] = True
        return jsonify(data)

    return redirect(url_for("home"))

@app.route("/ai_chat", methods=["POST"])
def ai_chat():
    if "username" not in session:
        return jsonify({"response": "Please log in first."})
        
    user = session["username"].strip().lower()
    msg = request.json.get("message", "").lower()
    
    # Query data to make insights feel custom and dynamic!
    data = get_dashboard_data(user)
    total = data["total_expenses"]
    top_cat = data["ai_insights"]["top_category"]
    
    if "save" in msg or "budget" in msg or "saving" in msg:
        if total > 5000:
            return jsonify({"response": f"Your current spending is ₹{total:.2f}. Try minimizing discretionary spend in '{top_cat}' to save up to 15% this month!"})
        return jsonify({"response": "Your spending is currently low and stable. Keep maintaining this pace, and focus on putting away 20% of your earnings."})
        
    if "category" in msg or "spend" in msg or "most" in msg:
        if top_cat != "None":
            return jsonify({"response": f"You spend the most in the '{top_cat}' category. Keep an eye on it to limit secondary expenses."})
        return jsonify({"response": "You haven't logged any expenses yet. Log your first expense, and I'll tell you about your top categories!"})
        
    return jsonify({"response": f"Hi! I see you have logged ₹{total:.2f} total expenses. Let me know if you would like automated tips on saving, or details on your categories!"})

@app.route("/delete_expense/<int:expense_index>", methods=["POST"])
def delete_expense(expense_index):
    if "username" not in session:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        return redirect(url_for("login"))
    
    user = session["username"].strip().lower()
    df = pd.read_csv(EXPENSES_FILE, dtype={"Username": str, "Category": str, "Description": str})
    df["Username"] = df["Username"].fillna("").str.strip().str.lower()
    
    if expense_index in df.index and df.loc[expense_index, "Username"] == user:
        df = df.drop(index=expense_index)
        df.to_csv(EXPENSES_FILE, index=False)
        
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.args.get("ajax") == "true":
            data = get_dashboard_data(user)
            data["success"] = True
            return jsonify(data)
            
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json or request.args.get("ajax") == "true":
        return jsonify({"success": False, "error": "Could not delete expense"})
        
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = pd.read_csv(USERS_FILE, dtype={"Username": str, "Password": str})
        users["Username"] = users["Username"].fillna("").str.strip().str.lower()
        users["Password"] = users["Password"].fillna("")

        u, p = request.form["username"].strip().lower(), request.form["password"]

        if u in users["Username"].values:
            stored = str(users.loc[users["Username"] == u, "Password"].values[0])
            
            try:
                is_valid = check_password_hash(stored, p)
            except ValueError:
                is_valid = False
                
            if is_valid:
                session["username"] = u
                return redirect(url_for("home"))
            elif stored == p:
                hashed = generate_password_hash(p)
                users.loc[users["Username"] == u, "Password"] = hashed
                users.to_csv(USERS_FILE, index=False)
                session["username"] = u
                return redirect(url_for("home"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users = pd.read_csv(USERS_FILE, dtype={"Username": str, "Password": str})
        users["Username"] = users["Username"].fillna("").str.strip().str.lower()
        
        u = request.form["username"].strip().lower()
        p = request.form["password"]
        
        if u in users["Username"].values:
            return render_template("register.html", error="User exists")

        new_row = pd.DataFrame([[u, generate_password_hash(p)]], columns=["Username", "Password"])
        users = pd.concat([users, new_row], ignore_index=True)
        users.to_csv(USERS_FILE, index=False)
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
