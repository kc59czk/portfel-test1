from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timezone
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'twoj_tajny_klucz'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_symbol = db.Column(db.String(10), nullable=False)  # np. CDR, PZU, PKO
    stock_name = db.Column(db.String(100))  # nazwa spółki
    amount = db.Column(db.Float, nullable=False)  # liczba akcji
    price_per_unit = db.Column(db.Float, nullable=False)  # cena za akcję w PLN
    transaction_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # data transakcji
    transaction_type = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'

def get_app_version():
    try:
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "dev"
    
def get_stock_price(symbol):
    symbol = symbol.upper()
    try:
        # API stooq.pl - format symbolu: CDR.WA dla CD Projekt na WGPW
        url = f"https://stooq.pl/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
        response = requests.get(url)

        # Parsowanie odpowiedzi CSV
        lines = response.text.split('\n')
        if len(lines) > 1:
            headers = lines[0].split(',')
            values = lines[1].split(',')
            data = dict(zip(headers, values))

            # Handle "B/D" (no data) case
            close_price = data.get('Zamkniecie', '0')
            if close_price == 'B/D':
                return None
            return float(close_price)
        return None
    except Exception as e:
        print(f"Błąd przy pobieraniu ceny dla {symbol}: {e}")
        return None

def get_stock_name(symbol):
    # Słownik z popularnymi spółkami - można rozszerzyć
    stock_names = {
        'CDR': 'CD Projekt',
        'PZU': 'PZU',
        'PKO': 'PKO BP',
        'PKN': 'PKN Orlen',
        'KGH': 'KGHM',
        'LPP': 'LPP',
        'DNP': 'Dino Polska',
        'ALE': 'Allegro',
        'OPL': 'Orange Polska',
        'PEO': 'Pepco'
    }
    return stock_names.get(symbol.upper(), symbol.upper())

# Dodaj nowy model
class PortfolioHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    total_value = db.Column(db.Float)
    total_invested = db.Column(db.Float)

# Funkcja do zapisywania historii portfela
def save_portfolio_history():
    transactions = Transaction.query.all()
    portfolio = {}
    total_value = 0.0
    total_invested = 0.0
    
    # Oblicz aktualną wartość portfela
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
    
    # Oblicz całkowitą wartość i zainwestowany kapitał
    for stock in portfolio:
        if portfolio[stock]['amount'] > 0:
            current_price = get_stock_price(stock)
            if current_price:
                current_value = portfolio[stock]['amount'] * current_price
                total_value += current_value
                total_invested += portfolio[stock]['invested']
    
    # Zapisz do historii
    history = PortfolioHistory(
        total_value=total_value,
        total_invested=total_invested
    )
    db.session.add(history)
    db.session.commit()

@app.route('/')
def index():
    transactions = Transaction.query.all()
    
    # Obliczanie statystyk portfela
    portfolio = {}
    total_value = 0.0  # Zainicjuj jako float
    total_invested = 0.0  # Zainicjuj jako float
    
    for tx in transactions:
        if tx.stock_symbol not in portfolio:
            portfolio[tx.stock_symbol] = {
                'amount': 0,
                'invested': 0,
                'current_price': get_stock_price(tx.stock_symbol),
                'name': tx.stock_name or get_stock_name(tx.stock_symbol)
            }
        
        if tx.transaction_type == 'buy':
            portfolio[tx.stock_symbol]['amount'] += tx.amount
            portfolio[tx.stock_symbol]['invested'] += tx.amount * tx.price_per_unit
        else:
            portfolio[tx.stock_symbol]['amount'] -= tx.amount
            portfolio[tx.stock_symbol]['invested'] -= tx.amount * tx.price_per_unit
    
    # Obliczanie aktualnej wartości i zysku/straty
    for stock in portfolio:
        # Dodaj tylko aktywa, które faktycznie posiadasz (amount > 0)
        if portfolio[stock]['amount'] > 0:
            if portfolio[stock]['current_price']:
                current_value = portfolio[stock]['amount'] * portfolio[stock]['current_price']
                portfolio[stock]['current_value'] = current_value
                portfolio[stock]['profit_loss'] = current_value - portfolio[stock]['invested']
                total_value += current_value
                total_invested += portfolio[stock]['invested']
            else:
                portfolio[stock]['current_value'] = None
                portfolio[stock]['profit_loss'] = None
    
    total_profit_loss = total_value - total_invested
    
    return render_template('index.html', 
                         portfolio=portfolio,
                         total_value=total_value,
                         total_invested=total_invested,
                         total_profit_loss=total_profit_loss,
                         transactions=transactions,
                         app_version=get_app_version())

@app.route('/charts')
def charts():
    transactions = Transaction.query.all()
    portfolio = {}
    # ... (taka sama logika obliczeń jak w index()) ...
    total_invested = 0.0
    total_value = 0.0  # Zainicjuj jako float
    
    for tx in transactions:
        if tx.stock_symbol not in portfolio:
            portfolio[tx.stock_symbol] = {
                'amount': 0,
                'invested': 0,
                'current_price': get_stock_price(tx.stock_symbol),
                'name': tx.stock_name or get_stock_name(tx.stock_symbol)
            }
        
        if tx.transaction_type == 'buy':
            portfolio[tx.stock_symbol]['amount'] += tx.amount
            portfolio[tx.stock_symbol]['invested'] += tx.amount * tx.price_per_unit
        else:
            portfolio[tx.stock_symbol]['amount'] -= tx.amount
            portfolio[tx.stock_symbol]['invested'] -= tx.amount * tx.price_per_unit
    
    # Obliczanie aktualnej wartości i zysku/straty
    for stock in portfolio:
        if portfolio[stock]['amount'] > 0:
          if portfolio[stock]['current_price'] and portfolio[stock]['amount'] > 0:
              current_value = portfolio[stock]['amount'] * portfolio[stock]['current_price']
              portfolio[stock]['current_value'] = current_value
              portfolio[stock]['profit_loss'] = current_value - portfolio[stock]['invested']
              total_value += current_value
              total_invested += portfolio[stock]['invested']
          else:
              portfolio[stock]['current_value'] = None
              portfolio[stock]['profit_loss'] = None
    
    total_profit_loss = total_value - total_invested if total_invested > 0 else 0
    history_records = PortfolioHistory.query.order_by(PortfolioHistory.date).all()
 
    history = []
    for record in history_records:
        history.append({
            "date": record.date.strftime("%Y-%m-%d %H:%M"),
            "total_value": record.total_value,
            "total_invested": record.total_invested
        })

    return render_template('charts.html', 
                          portfolio=portfolio,
                          history=history,
                          app_version=get_app_version())    


#    return render_template('charts.html', portfolio=portfolio)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol'].upper()
        stock_name = request.form.get('stock_name', '')
        amount = float(request.form['amount'])
        price_per_unit = float(request.form['price_per_unit'])
        transaction_type = request.form['transaction_type']
        
                # Pobierz datę transakcji z formularza
        transaction_date_str = request.form.get('transaction_date')
        
        # Konwertuj datę, jeśli została podana
        if transaction_date_str:
            try:
                # Format: 'YYYY-MM-DDTHH:MM'
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Nieprawidłowy format daty. Użyj bieżącej daty.', 'warning')
                transaction_date = datetime.now(timezone.utc)  # Użyj bieżącej daty w przypadku błędu

        else:
            transaction_date = datetime.now(timezone.utc)  # Użyj bieżącej daty, jeśli nie podano


        # Jeśli nazwa nie została podana, użyj domyślnej z słownika
        if not stock_name:
            stock_name = get_stock_name(stock_symbol)
        
        # Walidacja dla sprzedaży
        if transaction_type == 'sell':
            total_amount = sum(
                tx.amount for tx in Transaction.query.filter_by(
                    stock_symbol=stock_symbol,
                    transaction_type='buy'
                ).all()
            ) - sum(
                tx.amount for tx in Transaction.query.filter_by(
                    stock_symbol=stock_symbol,
                    transaction_type='sell'
                ).all()
            )
            
            if amount > total_amount:
                flash('Nie masz wystarczającej liczby akcji do sprzedaży!', 'danger')
                return redirect(url_for('add_transaction'))
        
        new_transaction = Transaction(
            stock_symbol=stock_symbol,
            stock_name=stock_name,
            amount=amount,
            price_per_unit=price_per_unit,
            transaction_type=transaction_type,
            transaction_date=transaction_date  # Użyj wybranej daty
        )
        
        db.session.add(new_transaction)
        db.session.commit()
        # Zapisz historię portfela po dodaniu transakcji        
        save_portfolio_history() 
        flash('Transakcja dodana pomyślnie!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_transaction.html',app_version=get_app_version())

@app.route('/delete_transaction/<int:id>')
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    save_portfolio_history() 
    flash('Transakcja usunięta pomyślnie!', 'success')
    return redirect(url_for('index'))

@app.route('/update_prices')
def update_prices():
    # Pobierz unikalne symbole z portfela
    transactions = Transaction.query.all()
    symbols = list(set([tx.stock_symbol for tx in transactions]))
    
    # Pobierz aktualne ceny dla każdego symbolu
    updated_prices = {}
    for symbol in symbols:
        updated_prices[symbol] = get_stock_price(symbol)
    
    flash('Ceny akcji zostały zaktualizowane!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
