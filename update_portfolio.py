import os
from datetime import datetime, timezone
from app import app, db, Transaction, PortfolioHistory, get_stock_price

def update_all_users_portfolio():
    with app.app_context():
        users = db.session.query(Transaction.user_email).distinct()
        for user_row in users:
            user = user_row.user_email
            transactions = Transaction.query.filter_by(user_email=user).all()
            portfolio = {}
            total_value = 0.0
            total_invested = 0.0

            for tx in transactions:
                if tx.stock_symbol not in portfolio:
                    portfolio[tx.stock_symbol] = {
                        'amount': 0,
                        'invested': 0
                    }
                if tx.transaction_type == 'buy':
                    portfolio[tx.stock_symbol]['amount'] += tx.amount
                    portfolio[tx.stock_symbol]['invested'] += tx.amount * tx.price_per_unit
                else:
                    portfolio[tx.stock_symbol]['amount'] -= tx.amount
                    portfolio[tx.stock_symbol]['invested'] -= tx.amount * tx.price_per_unit

            for stock in portfolio:
                if portfolio[stock]['amount'] > 0:
                    current_price = get_stock_price(stock)
                    if current_price:
                        current_value = portfolio[stock]['amount'] * current_price
                        total_value += current_value
                        total_invested += portfolio[stock]['invested']

            # Save snapshot to PortfolioHistory
            history = PortfolioHistory(
                total_value=total_value,
                total_invested=total_invested,
                user_email=user,
                date=datetime.now(timezone.utc)
            )
            db.session.add(history)
        db.session.commit()
        print("Portfolio history updated for all users.")

if __name__ == "__main__":
    update_all_users_portfolio()