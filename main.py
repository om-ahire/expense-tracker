import pandas as pd
from datetime import datetime
import os

# File to store expenses
FILE_NAME = "data.csv"

# Create file if it doesn't exist
if not os.path.exists(FILE_NAME):
    df = pd.DataFrame(columns=["Date", "Amount", "Category", "Description"])
    df.to_csv(FILE_NAME, index=False)


def add_expense():
    date = input("Enter date (YYYY-MM-DD) or leave blank for today: ")
    if date.strip() == "":
        date = datetime.today().strftime('%Y-%m-%d')

    amount = float(input("Enter amount: "))
    category = input("Enter category (Food, Travel, Bills, etc.): ")
    description = input("Enter description: ")

    new_expense = pd.DataFrame([[date, amount, category, description]],
                               columns=["Date", "Amount", "Category", "Description"])

    new_expense.to_csv(FILE_NAME, mode='a', header=False, index=False)
    print("\n✅ Expense added successfully!\n")


def view_expenses():
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        print("\nNo expenses recorded yet!\n")
    else:
        print("\n📋 Your Expenses:\n")
        print(df.to_string(index=False))


def main():
    while True:
        print("\n--- PERSONAL EXPENSE TRACKER ---")
        print("1. Add Expense")
        print("2. View Expenses")
        print("3. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid choice! Try again.\n")


if __name__ == "__main__":
    main()
