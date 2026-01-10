from flask import Flask, render_template, url_for, request, jsonify
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.database.db_manager import DatabaseManager
from src.ai.price_predictor import PricePredictor

app = Flask(__name__)
db = DatabaseManager()

#helpers
def get_chart_data(conn):
    dates, prices = [], []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATE(scraped_at) as day, AVG(price) FROM market_data GROUP BY day ORDER BY day DESC LIMIT 7")
            rows = cur.fetchall()
            for r in rows:
                dates.append(r[0].strftime('%b %d'))
                prices.append(float(r[1]))
            dates.reverse()
            prices.reverse()
    except: pass
    return dates, prices

def get_movers(conn):
    movers = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM products LIMIT 50")
            products = cur.fetchall()
            for pid, name in products:
                cur.execute("SELECT price FROM market_data WHERE product_id = %s ORDER BY scraped_at DESC LIMIT 2", (pid,))
                prices = [row[0] for row in cur.fetchall()]
                if len(prices) == 2:
                    current, old = float(prices[0]), float(prices[1])
                    if old > 0:
                        pct = ((current - old) / old) * 100
                        if abs(pct) > 0.1:
                            movers.append({
                                'short_name': name[:15] + '..' if len(name) > 15 else name,
                                'price': f"LKR {current:,.0f}",
                                'change': f"{pct:+.1f}%",
                                'trend': 'up' if pct > 0 else 'down',
                                'abs_change': abs(pct)
                            })
            movers.sort(key=lambda x: x['abs_change'], reverse=True)
            return movers[:5]
    except: return []

#discovery feed
def get_discovery_feed(conn):
    feed_items = []
    try:
        with conn.cursor() as cur:
            #get products
            cur.execute("SELECT id, name FROM products LIMIT 100")
            products = cur.fetchall()
            
            scored_items = []
            for pid, name in products:
                cur.execute("""
                    SELECT price, vendor_name, is_in_stock 
                    FROM market_data 
                    WHERE product_id = %s 
                    ORDER BY scraped_at DESC LIMIT 2
                """, (pid,))
                rows = cur.fetchall()
                
                if rows:
                    current_price = float(rows[0][0])
                    vendor = rows[0][1]
                    stock = rows[0][2]
                    
                    # Calc volatility
                    score = 0
                    if len(rows) == 2:
                        old_price = float(rows[1][0])
                        score = abs(current_price - old_price)
                    
                    scored_items.append({
                        'id': pid,
                        'name': name,
                        'price': f"{current_price:,.0f}",
                        'vendor': vendor,
                        'stock': stock,
                        'score': score
                    })
            
            #Sort by Volatility
            scored_items.sort(key=lambda x: x['score'], reverse=True)
            
            #get top 8
            feed_items = scored_items[:8]
            
            if not feed_items:
                feed_items = scored_items[:8]
                
    except: pass
    return feed_items

#context processor
@app.context_processor
def inject_global_data():
    conn = db.get_connection()
    vendors = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT vendor_name FROM market_data WHERE vendor_name != 'TestVendor' LIMIT 5")
            vendors = [row[0] for row in cur.fetchall()]
    except: vendors = ['Demo: Amazon', 'Demo: BestBuy']
    
    if conn:
        conn.close()
        
    return dict(vendor_list=vendors, server_status={'db': 'Online', 'ai': 'Ready v1.0', 'sync': 'Live'})

#dashboard route
@app.route('/')
def dashboard():
    conn = db.get_connection()
    stats = {'products': 0, 'stock_alerts': 0}
    chart_data = {'labels': [], 'prices': []}
    movers_data = []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT id) FROM products")
            res = cur.fetchone()
            if res: stats['products'] = res[0]
            
            cur.execute("SELECT COUNT(*) FROM market_data WHERE is_in_stock = FALSE AND scraped_at > NOW() - INTERVAL '24 HOURS'")
            res = cur.fetchone()
            if res: stats['stock_alerts'] = res[0]

        dates, price_list = get_chart_data(conn)
        if dates: 
            chart_data = {'labels': dates, 'prices': price_list}
        else:
            chart_data = {'labels': ['Mon','Tue','Wed'], 'prices': [120000, 125000, 122000]} 

        movers_data = get_movers(conn)
        if not movers_data:
            movers_data = [{'short_name': 'Demo: Ryzen', 'price': 'LKR 125k', 'change': '+1%', 'trend': 'up'}]

    except Exception as e:
        print(f"Error: {e}")
    finally:

        if conn:
            conn.close()

    return render_template('market_overview.html', stats=stats, chart_data=chart_data, movers=movers_data, active_page='dashboard')

#price explorer route
@app.route('/explorer')
def price_explorer():
    query = request.args.get('q', '').strip()
    tiers = {
        'premium': {'listings': [], 'avg': 0},
        'standard': {'listings': [], 'avg': 0},
        'value': {'listings': [], 'avg': 0}
    }
    search_stats = {'count': 0, 'min': '0', 'max': '0'}
    watchlist = [] 
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            if query:
                #search
                sql = """
                    SELECT p.id, p.name, p.brand, m.price, m.vendor_name, m.is_in_stock
                    FROM products p
                    JOIN market_data m ON p.id = m.product_id
                    WHERE p.name ILIKE %s
                    ORDER BY m.price DESC
                """
                cur.execute(sql, (f'%{query}%',))
                rows = cur.fetchall()
                
                results = []
                seen = set()
                prices = []
                for r in rows:
                    if r[0] not in seen:
                        results.append({
                            'id': r[0], 'name': r[1], 'brand': r[2],
                            'price': float(r[3]), 'price_fmt': f"{float(r[3]):,.0f}",
                            'vendor': r[4], 'stock': r[5]
                        })
                        seen.add(r[0])
                        prices.append(float(r[3]))
                
                search_stats['count'] = len(results)
                if prices:
                    search_stats['min'] = f"{min(prices):,.0f}"
                    search_stats['max'] = f"{max(prices):,.0f}"

                #tier logic
                count = len(results)
                if count > 0:
                    p_end = count // 3
                    s_end = (count * 2) // 3
                    tiers['premium']['listings'] = results[:p_end]
                    tiers['standard']['listings'] = results[p_end:s_end]
                    tiers['value']['listings'] = results[s_end:]
                    
                    for t in tiers:
                        lst = tiers[t]['listings']
                        if lst:
                            avg = sum(x['price'] for x in lst) / len(lst)
                            tiers[t]['avg'] = f"{avg:,.0f}"
                        else:
                            tiers[t]['avg'] = "0"
            else:
                #default discovery feed
                watchlist = get_discovery_feed(conn)

    except Exception as e:
        print(f"Error: {e}")
    finally:

        if conn:
            conn.close()

    return render_template('price_explorer.html', 
                         active_page='explorer', 
                         query=query, 
                         tiers=tiers, 
                         search_stats=search_stats,
                         watchlist=watchlist)

#routes api
@app.route('/api/analyze_tier', methods=['POST'])
def api_analyze_tier():
    data = request.json
    product_ids = data.get('ids', [])
    predictor = PricePredictor()
    result = predictor.predict_group(product_ids)
    dates, prices, recommendation = [], [], "Insufficient Data"
    if result:
        current, target = result['current_price'], result['predicted_price_7_days']
        recommendation = result['recommendation']
        if -1.0 <= result['percent_change'] <= 1.0:
            target = current
            recommendation = "⚖️ SAFE (Stable Market)"
        step = (target - current) / 7
        start = datetime.now()
        for i in range(1, 8):
            dates.append((start + timedelta(days=i)).strftime('%b %d'))
            prices.append(current + (step * i))
    else:
        for i in range(1,8): dates.append(f"Day {i}"); prices.append(0)
    return jsonify({'dates': dates, 'prices': prices, 'recommendation': recommendation})

@app.route('/api/analyze/<int:product_id>')
def api_analyze_single(product_id):
    predictor = PricePredictor()
    result = predictor.predict_single(product_id)
    dates, prices, recommendation = [], [], "No Data"
    if result:
        current, target = result['current_price'], result['predicted_price_7_days']
        recommendation = result['recommendation']
        if -1.0 <= result['percent_change'] <= 1.0:
            target = current
            recommendation = "⚖️ SAFE (Stable Market)"
        step = (target - current) / 7
        start = datetime.now()
        for i in range(1, 8):
            dates.append((start + timedelta(days=i)).strftime('%b %d'))
            prices.append(current + (step * i))
    else:
        for i in range(1,8): dates.append(f"Day {i}"); prices.append(0)
    return jsonify({'dates': dates, 'prices': prices, 'recommendation': recommendation})

if __name__ == '__main__':
    app.run(debug=True)