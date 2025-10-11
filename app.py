from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import pandas as pd
from datetime import datetime, timedelta
import json
import re
from collections import Counter
import numpy as np

app = Flask(__name__)
app.secret_key = "supersecretkey"

USERS_FILE = "users.csv"
EXPENSES_FILE = "expenses.csv"

# Make sure files exist
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["Username", "Password"]
                 ).to_csv(USERS_FILE, index=False)

if not os.path.exists(EXPENSES_FILE):
    pd.DataFrame(columns=["Username", "Date", "Amount", "Category",
                 "Description"]).to_csv(EXPENSES_FILE, index=False)


# AI-Powered Functions
class ExpenseAI:
    def __init__(self):
        self.category_keywords = {
            'Food': ['restaurant', 'food', 'meal', 'lunch', 'dinner', 'breakfast', 'cafe', 'coffee', 'pizza', 'burger', 'grocery', 'supermarket', 'dining'],
            'Transportation': ['uber', 'taxi', 'bus', 'train', 'metro', 'gas', 'fuel', 'parking', 'toll', 'flight', 'airline', 'car', 'transport'],
            'Entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'game', 'concert', 'theater', 'sports', 'gym', 'fitness', 'entertainment'],
            'Shopping': ['amazon', 'store', 'shopping', 'mall', 'clothes', 'fashion', 'electronics', 'book', 'retail'],
            'Bills': ['electricity', 'water', 'internet', 'phone', 'rent', 'mortgage', 'insurance', 'bill', 'utility'],
            'Healthcare': ['doctor', 'hospital', 'pharmacy', 'medicine', 'medical', 'health', 'dental', 'clinic'],
            'Travel': ['hotel', 'booking', 'travel', 'vacation', 'trip', 'airbnb', 'flight', 'tourism'],
            'Education': ['school', 'university', 'course', 'book', 'education', 'learning', 'tuition'],
            'Other': []
        }

    def smart_categorize(self, description, amount):
        """AI-powered expense categorization"""
        description_lower = description.lower()

        # Check for exact keyword matches
        for category, keywords in self.category_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return category

        # Amount-based categorization for common patterns
        if amount > 1000:
            return 'Bills' if any(word in description_lower for word in ['rent', 'mortgage', 'insurance']) else 'Other'
        elif amount < 10:
            return 'Food' if any(word in description_lower for word in ['coffee', 'snack', 'drink']) else 'Other'

        return 'Other'

    def get_spending_insights(self, expenses_df):
        """Generate AI-powered spending insights"""
        if expenses_df.empty:
            return {
                'total_spent': 0,
                'avg_daily': 0,
                'top_category': None,
                'spending_trend': 'stable',
                'recommendations': ['Start tracking your expenses to get personalized insights!']
            }

        try:
            # Ensure Date column is datetime
            expenses_df = expenses_df.copy()
            expenses_df['Date'] = pd.to_datetime(expenses_df['Date'])

            total_spent = expenses_df['Amount'].sum()
            avg_daily = total_spent / 30  # Assuming 30-day period

            category_spending = expenses_df.groupby(
                'Category')['Amount'].sum().sort_values(ascending=False)
            top_category = category_spending.index[0] if not category_spending.empty else None

            # Calculate spending trend
            recent_expenses = expenses_df[expenses_df['Date'] >= (
                datetime.now() - timedelta(days=7))]['Amount'].sum()
            previous_expenses = expenses_df[(expenses_df['Date'] >= (datetime.now() - timedelta(days=14))) &
                                            (expenses_df['Date'] < (datetime.now() - timedelta(days=7)))]['Amount'].sum()

            if recent_expenses > previous_expenses * 1.2:
                trend = 'increasing'
            elif recent_expenses < previous_expenses * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'

            # Generate recommendations
            recommendations = []
            if total_spent > 2000:
                recommendations.append(
                    "💡 Consider reviewing your spending patterns - you've spent over ₹2000 this month")
            if top_category and category_spending[top_category] > total_spent * 0.4:
                recommendations.append(
                    f"🎯 {top_category} is your biggest expense category - consider budgeting for it")
            if avg_daily > 50:
                recommendations.append(
                    "📊 Your daily average spending is high - try setting daily spending limits")
            if trend == 'increasing':
                recommendations.append(
                    "⚠️ Your spending trend is increasing - consider reviewing your budget")

            return {
                'total_spent': total_spent,
                'avg_daily': avg_daily,
                'top_category': top_category,
                'spending_trend': trend,
                'recommendations': recommendations
            }
        except Exception as e:
            # Return default values if there's an error
            return {
                'total_spent': 0,
                'avg_daily': 0,
                'top_category': None,
                'spending_trend': 'stable',
                'recommendations': ['Unable to analyze spending patterns at this time.']
            }

    def predict_monthly_budget(self, expenses_df):
        """Predict monthly budget based on historical data"""
        if expenses_df.empty:
            return 1000  # Default budget

        try:
            monthly_totals = expenses_df.groupby(
                pd.to_datetime(expenses_df['Date']).dt.to_period('M'))['Amount'].sum()
            if len(monthly_totals) >= 2:
                return int(monthly_totals.mean() * 1.1)  # 10% buffer
            return int(expenses_df['Amount'].sum() * 1.1)
        except Exception as e:
            return 1000  # Return default budget if there's an error


# Initialize AI
expense_ai = ExpenseAI()


@app.route("/")
def home():
    if "username" in session:
        username = session["username"]

        # Get user's expenses
        expenses_df = pd.read_csv(EXPENSES_FILE)
        user_expenses = expenses_df[expenses_df["Username"] == username]

        # Calculate statistics
        total_expenses = user_expenses["Amount"].sum(
        ) if not user_expenses.empty else 0
        if not user_expenses.empty:
            user_expenses['Date'] = pd.to_datetime(user_expenses['Date'])
            current_month = datetime.now().strftime("%Y-%m")
            monthly_expenses = user_expenses[user_expenses["Date"].dt.to_period(
                'M').astype(str).str.startswith(current_month)]["Amount"].sum()
        else:
            monthly_expenses = 0

        # Get category breakdown
        category_data = user_expenses.groupby(
            "Category")["Amount"].sum().to_dict() if not user_expenses.empty else {}

        # Get recent expenses (last 5) with indices for deletion
        if not user_expenses.empty:
            recent_expenses_data = user_expenses.tail(5)
            recent_expenses = []
            for idx, row in recent_expenses_data.iterrows():
                expense_dict = row.to_dict()
                expense_dict['index'] = idx  # Add index for deletion
                recent_expenses.append(expense_dict)
        else:
            recent_expenses = []

        # Get AI insights
        ai_insights = expense_ai.get_spending_insights(user_expenses)
        predicted_budget = expense_ai.predict_monthly_budget(user_expenses)

        return render_template("index.html",
                               username=username,
                               total_expenses=total_expenses,
                               monthly_expenses=monthly_expenses,
                               category_data=category_data,
                               recent_expenses=recent_expenses,
                               current_date=datetime.now().strftime('%Y-%m-%d'),
                               ai_insights=ai_insights,
                               predicted_budget=predicted_budget)
    else:
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # Validate input
        if not username or not password:
            return render_template("login.html", error="Please fill in all fields!")

        users = pd.read_csv(USERS_FILE)

        if username in users["Username"].values:
            stored_pass = str(
                users.loc[users["Username"] == username, "Password"].values[0])
            if password == stored_pass:
                session["username"] = username
                return redirect(url_for("home"))

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # Validate input
        if not username or not password:
            return render_template("register.html", error="Please fill in all fields!")

        if len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters long!")

        if len(password) < 4:
            return render_template("register.html", error="Password must be at least 4 characters long!")

        users = pd.read_csv(USERS_FILE)

        if username in users["Username"].values:
            return render_template("register.html", error="Username already exists!")

        new_user = pd.DataFrame([[username, str(password)]], columns=[
                                "Username", "Password"])
        users = pd.concat([users, new_user], ignore_index=True)
        users.to_csv(USERS_FILE, index=False)

        return render_template("register.html", success="Account created successfully! You can now login.")

    return render_template("register.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # Validate input
        if not username or not password:
            return render_template("signup.html", error="Please fill in all fields!")

        if len(username) < 3:
            return render_template("signup.html", error="Username must be at least 3 characters long!")

        if len(password) < 4:
            return render_template("signup.html", error="Password must be at least 4 characters long!")

        users = pd.read_csv(USERS_FILE)

        if username in users["Username"].values:
            return render_template("signup.html", error="Username already exists!")

        new_user = pd.DataFrame([[username, str(password)]], columns=[
                                "Username", "Password"])
        users = pd.concat([users, new_user], ignore_index=True)
        users.to_csv(USERS_FILE, index=False)

        return render_template("signup.html", success="Account created successfully! You can now login.")

    return render_template("signup.html")


@app.route("/add_expense", methods=["POST"])
def add_expense():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    date = request.form.get("date", datetime.today().strftime('%Y-%m-%d'))
    amount = float(request.form["amount"])
    category = request.form["category"]
    description = request.form["description"]

    # AI-powered smart categorization if category is "Other" or empty
    if category == "Other" or not category:
        category = expense_ai.smart_categorize(description, amount)

    new_expense = pd.DataFrame([[username, date, amount, category, description]],
                               columns=["Username", "Date", "Amount", "Category", "Description"])

    expenses_df = pd.read_csv(EXPENSES_FILE)
    expenses_df = pd.concat([expenses_df, new_expense], ignore_index=True)
    expenses_df.to_csv(EXPENSES_FILE, index=False)

    return redirect(url_for("home"))


@app.route("/get_expenses")
def get_expenses():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"})

    username = session["username"]
    expenses_df = pd.read_csv(EXPENSES_FILE)
    user_expenses = expenses_df[expenses_df["Username"] == username]

    return jsonify(user_expenses.to_dict('records'))


@app.route("/delete_expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    expenses_df = pd.read_csv(EXPENSES_FILE)

    # Filter out the expense to delete (using index as ID)
    if expense_id < len(expenses_df):
        expenses_df = expenses_df.drop(expenses_df.index[expense_id])
        expenses_df.to_csv(EXPENSES_FILE, index=False)

    return redirect(url_for("home"))


@app.route("/ai_chat", methods=["POST"])
def ai_chat():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"})

    username = session["username"]
    user_message = request.json.get("message", "").lower()

    # Get user's expense data for context
    expenses_df = pd.read_csv(EXPENSES_FILE)
    user_expenses = expenses_df[expenses_df["Username"] == username]

    # AI-powered responses based on user queries
    responses = {
        "budget": f"Based on your spending patterns, I recommend a monthly budget of ₹{expense_ai.predict_monthly_budget(user_expenses)}. Your current spending trend is {expense_ai.get_spending_insights(user_expenses)['spending_trend']}.",
        "spending": f"You've spent ₹{user_expenses['Amount'].sum():.2f} total. Your top category is {expense_ai.get_spending_insights(user_expenses)['top_category'] or 'not available'}.",
        "save": "To save money, consider: 1) Track daily expenses, 2) Set category budgets, 3) Review spending patterns weekly, 4) Use the 50/30/20 rule (50% needs, 30% wants, 20% savings).",
        "help": "I'm your KharchaMeter AI assistant! I can help you with: budget planning, spending analysis, expense categorization, saving tips, and financial insights. Just ask me anything about your expenses!",
        "categories": "Your main expense categories are: " + ", ".join(user_expenses['Category'].unique()) if not user_expenses.empty else "No expenses tracked yet."
    }

    # Find best response
    response = "Welcome to KharchaMeter! I'm here to help with your expense management. Ask me about budgets, spending patterns, or saving tips."
    for keyword, reply in responses.items():
        if keyword in user_message:
            response = reply
            break

    return jsonify({"response": response})


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
