from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import os
import hmac
import hashlib
try:
    import razorpay
except ImportError:
    razorpay = None
BASE_DIR = Path(__file__).resolve().parent

if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/brandboost.db")
else:
    DB_PATH = BASE_DIR / "brandboost.db"
app = Flask(__name__)
app.secret_key = os.environ.get('BRANDBOOST_SECRET_KEY', 'change-this-secret-before-deployment')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
PACKAGES = {
    'trial': {
        'name': '7-Day Free Trial',
        'price': 0,
        'offer': 'Free mini brand audit + 3 content ideas',
        'items': ['7-day access', 'Starter audit', '3 content ideas'],
    },
    'starter': {
        'name': 'Starter Spark',
        'price': 399,
        'offer': 'Free mini audit + 5 caption ideas',
        'items': [
            'Profile & identity review',
            '5 caption ideas',
            'Content pillar setup',
            'Brand Pulse access',
        ],
    },
    'growth': {
        'name': 'Growth Builder',
        'price': 699,
        'offer': 'Free audit + 1 bonus content-calendar week',
        'items': [
            'Everything in Starter',
            'Monthly content direction',
            'Bonus calendar week',
            'Lead CTA review',
        ],
    },
    'pro': {
        'name': 'Brand Pro',
        'price': 999,
        'offer': 'Free audit + 2 strategy calls + 10 bonus ideas',
        'items': [
            'Everything in Growth',
            '2 strategy calls',
            '10 bonus content ideas',
            'Campaign review',
        ],
    },
}

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            trial_started TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            package_key TEXT,
            package_name TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'Pending',
            payment_method TEXT DEFAULT 'Not selected',
            gateway_order_id TEXT,
            payment_id TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            brand_name TEXT,
            platform TEXT,
            goal TEXT,
            audience TEXT,
            presence TEXT,
            score INTEGER,
            recommendation TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            email TEXT,
            message TEXT,
            reply TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            platform TEXT,
            tone TEXT,
            goal TEXT,
            idea TEXT,
            attention INTEGER,
            trust INTEGER,
            conversion INTEGER,
            risk INTEGER,
            recommendation TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS dna_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            brand_name TEXT,
            tone TEXT,
            colors TEXT,
            keywords TEXT,
            idea TEXT,
            score INTEGER,
            recommendation TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS site_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mood_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            brand_name TEXT,
            mood TEXT,
            goal TEXT,
            audience TEXT,
            score INTEGER,
            style_direction TEXT,
            content_direction TEXT,
            created_at TEXT
        );
        """
    )
    default_settings = {
        'site_name': 'BrandBoost',
        'tagline': 'Affordable, student-focused social media branding.',
        'hero_title': 'Turn your online presence into business growth.',
        'hero_text': 'BrandBoost helps students, freelancers and small businesses build a professional brand, increase visibility and generate potential customers.',
        'primary_color': '#6d4aff',
        'accent_color': '#1c9a67',
        'style_name': 'Modern & Creative',
    }
    for setting_key, setting_value in default_settings.items():
        c.execute(
            'INSERT OR IGNORE INTO site_settings(setting_key, setting_value) VALUES (?, ?)',
            (setting_key, setting_value),
        )
    existing_columns = {row['name'] for row in c.execute('PRAGMA table_info(orders)').fetchall()}
    for column, definition in [('payment_method', "TEXT DEFAULT 'Not selected'"), ('gateway_order_id', 'TEXT'), ('payment_id', 'TEXT')]:
        if column not in existing_columns:
            c.execute(f'ALTER TABLE orders ADD COLUMN {column} {definition}')
    if not c.execute('SELECT id FROM users WHERE email=?', ('admin@brandboost.local',)).fetchone():
        c.execute('INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)', ('BrandBoost Admin', 'admin@brandboost.local', generate_password_hash('admin123'), 'admin', datetime.now().isoformat(timespec='seconds')))
    c.commit()
    c.close()

def user():
    if not session.get('uid'):
        return None
    c = db()
    u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
    c.close()
    return u

def get_site_settings():
    """Return editable website appearance and copy settings from SQLite."""
    connection = db()
    rows = connection.execute('SELECT setting_key, setting_value FROM site_settings').fetchall()
    connection.close()
    settings = {row['setting_key']: row['setting_value'] for row in rows}
    settings.setdefault('site_name', 'BrandBoost')
    settings.setdefault('tagline', 'Affordable, student-focused social media branding.')
    settings.setdefault('hero_title', 'Turn your online presence into business growth.')
    settings.setdefault('hero_text', 'BrandBoost helps students, freelancers and small businesses build a professional brand, increase visibility and generate potential customers.')
    settings.setdefault('primary_color', '#6d4aff')
    settings.setdefault('accent_color', '#1c9a67')
    settings.setdefault('style_name', 'Modern & Creative')
    return settings


@app.context_processor
def globals():
    settings = get_site_settings()
    return {
        'current_user': user(),
        'packages': PACKAGES,
        'site_settings': settings,
    }

def need_login():
    if not session.get('uid'):
        flash('Please login to continue.', 'warning')
        return False
    return True

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        if not name or not email or len(pw) < 6:
            flash('Enter valid details and a password of at least 6 characters.', 'danger')
        else:
            c = db()
            try:
                c.execute('INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)', (name, email, generate_password_hash(pw), datetime.now().isoformat(timespec='seconds')))
                c.commit()
                flash('Account created. Please login.', 'success')
                c.close()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.', 'danger')
                c.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw = request.form.get('password', '')
        c = db()
        u = c.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        c.close()
        if u and check_password_hash(u['password'], pw):
            session['uid'] = u['id']
            session['role'] = u['role']
            flash('Welcome to BrandBoost.', 'success')
            return redirect(url_for('admin') if u['role'] == 'admin' else url_for('dashboard'))
        flash('Incorrect email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not need_login():
        return redirect(url_for('login'))
    u = user()
    c = db()
    orders = c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    audits = c.execute('SELECT * FROM audits WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    chats = c.execute('SELECT * FROM chats WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    sims = c.execute('SELECT * FROM simulations WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    dna_checks = c.execute('SELECT * FROM dna_checks WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    mood_checks = c.execute('SELECT * FROM mood_checks WHERE user_id=? ORDER BY id DESC', (u['id'],)).fetchall()
    c.close()
    trial = None
    if u['trial_started']:
        days = max(0, 7 - (datetime.now() - datetime.fromisoformat(u['trial_started'])).days)
        trial = {'active': days > 0, 'remaining': days}
    return render_template('dashboard.html', user=u, orders=orders, audits=audits, chats=chats, simulations=sims, dna_checks=dna_checks, mood_checks=mood_checks, trial=trial)

@app.route('/trial', methods=['POST'])
def trial():
    if not need_login():
        return redirect(url_for('login'))
    c = db()
    u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
    if u['trial_started']:
        flash('Your free trial has already been activated.', 'info')
    else:
        c.execute('UPDATE users SET trial_started=? WHERE id=?', (datetime.now().isoformat(timespec='seconds'), u['id']))
        c.commit()
        flash('7-day free trial activated!', 'success')
    c.close()
    return redirect(url_for('dashboard'))

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/order/<key>', methods=['POST'])
def order(key):
    """Send a selected plan to checkout; no payment is taken on this route."""
    if key not in PACKAGES:
        flash('Package not found.', 'danger')
        return redirect(url_for('pricing'))
    if not need_login():
        return redirect(url_for('login'))
    if key == 'trial':
        return redirect(url_for('trial'))
    return redirect(url_for('checkout', key=key))

@app.route('/checkout/<key>', methods=['GET', 'POST'])
def checkout(key):
    if key not in PACKAGES or key == 'trial':
        flash('Please select a valid paid package.', 'danger')
        return redirect(url_for('pricing'))
    if not need_login():
        return redirect(url_for('login'))
    package = PACKAGES[key]
    gateway_ready = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and razorpay)
    gateway_order = None
    if request.method == 'POST':
        if request.form.get('payment_mode') == 'demo':
            connection = db()
            connection.execute(
                """INSERT INTO orders
                (user_id, package_key, package_name, amount, status,
                 payment_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session['uid'],
                    key,
                    package['name'],
                    package['price'],
                    'Demo Confirmed - Not Paid',
                    'Classroom Demo',
                    datetime.now().isoformat(timespec='seconds'),
                ),
            )
            connection.commit()
            connection.close()
            flash('Demo order saved. No real payment was taken.', 'info')
            return redirect(url_for('dashboard'))
        if not gateway_ready:
            flash('Online payment is not configured yet. Use demo checkout for your teacher showcase, or add Razorpay test keys in environment variables.', 'warning')
            return redirect(url_for('checkout', key=key))
    if gateway_ready:
        try:
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
            gateway_order = client.order.create(
                {
                    'amount': int(package['price']) * 100,
                    'currency': 'INR',
                    'receipt': (
                        f"bb-{session['uid']}-{key}-"
                        f"{int(datetime.now().timestamp())}"
                    ),
                    'notes': {
                        'user_id': str(session['uid']),
                        'package_key': key,
                    },
                }
            )
            connection = db()
            connection.execute(
                """INSERT INTO orders
                (user_id, package_key, package_name, amount, status,
                 payment_method, gateway_order_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session['uid'],
                    key,
                    package['name'],
                    package['price'],
                    'Pending',
                    'Razorpay',
                    gateway_order['id'],
                    datetime.now().isoformat(timespec='seconds'),
                ),
            )
            connection.commit()
            connection.close()
        except Exception:
            app.logger.exception('Could not create Razorpay order')
            flash('Payment gateway could not start. Check your Razorpay test credentials and try again.', 'danger')
    return render_template(
        'checkout.html',
        package=package,
        package_key=key,
        gateway_ready=gateway_ready,
        razorpay_key_id=RAZORPAY_KEY_ID,
        gateway_order=gateway_order,
        demo_mode=not gateway_ready,
    )

@app.route('/payment/verify', methods=['POST'])
def payment_verify():
    if not need_login():
        return redirect(url_for('login'))
    if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and razorpay):
        flash('Online payment is not configured.', 'warning')
        return redirect(url_for('pricing'))
    key = request.form.get('package_key', '')
    payment_id = request.form.get('razorpay_payment_id', '')
    gateway_order_id = request.form.get('razorpay_order_id', '')
    signature = request.form.get('razorpay_signature', '')
    if key not in PACKAGES or not all([payment_id, gateway_order_id, signature]):
        flash('Payment verification details are incomplete.', 'danger')
        return redirect(url_for('pricing'))
    message = f'{gateway_order_id}|{payment_id}'.encode('utf-8')
    expected_signature = hmac.new(RAZORPAY_KEY_SECRET.encode('utf-8'), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        flash('Payment signature verification failed. No paid order was saved.', 'danger')
        return redirect(url_for('checkout', key=key))
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        payment_details = client.payment.fetch(payment_id)
    except Exception:
        app.logger.exception('Could not retrieve Razorpay payment details')
        flash('Payment details could not be confirmed. Please contact support before retrying.', 'danger')
        return redirect(url_for('checkout', key=key))
    payment_matches_order = payment_details.get('order_id') == gateway_order_id
    payment_matches_amount = (
        int(payment_details.get('amount', 0))
        == int(PACKAGES[key]['price']) * 100
    )
    payment_is_captured = payment_details.get('status') == 'captured'

    if not (payment_matches_order and payment_matches_amount and payment_is_captured):
        flash('The gateway has not confirmed a captured payment for this package. The order remains unpaid.', 'danger')
        return redirect(url_for('checkout', key=key))
    package = PACKAGES[key]
    connection = db()
    pending_order = connection.execute(
        """SELECT id
           FROM orders
           WHERE user_id = ?
             AND package_key = ?
             AND gateway_order_id = ?
             AND status = 'Pending'
             AND amount = ?""",
        (session['uid'], key, gateway_order_id, package['price']),
    ).fetchone()
    if not pending_order:
        connection.close()
        flash('This payment order could not be matched to your account. Please start checkout again.', 'danger')
        return redirect(url_for('checkout', key=key))
    connection.execute(
        """UPDATE orders
           SET status = 'Paid', payment_id = ?
           WHERE id = ?""",
        (payment_id, pending_order['id']),
    )
    connection.commit()
    connection.close()
    flash('Payment verified and order saved successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/audit', methods=['GET', 'POST'])
def audit():
    result = None
    if request.method == 'POST':
        brand = request.form.get('brand_name', '').strip()
        platform = request.form.get('platform', '')
        goal = request.form.get('goal', '')
        audience = request.form.get('audience', '').strip()
        presence = request.form.get('presence', '')
        if not all([brand, platform, goal, audience, presence]):
            flash('Complete all audit fields.', 'danger')
        else:
            score = 48 + (8 if platform in ['Instagram', 'LinkedIn', 'YouTube'] else 0) + (8 if goal in ['Leads', 'Sales'] else 0) + (8 if len(audience) > 20 else 0) + (-8 if presence == 'Inconsistent' else 0) + random.randint(-3, 6)
            score = max(35, min(94, score))
            rec = 'Build 3 content pillars, keep visuals consistent and use one clear CTA.' if score < 70 else 'Strong base. Improve consistency, proof points and conversion CTAs.'
            c = db()
            c.execute('INSERT INTO audits(user_id,brand_name,platform,goal,audience,presence,score,recommendation,created_at) VALUES(?,?,?,?,?,?,?,?,?)', (session.get('uid'), brand, platform, goal, audience, presence, score, rec, datetime.now().isoformat(timespec='seconds')))
            c.commit()
            c.close()
            result = {'brand': brand, 'score': score, 'recommendation': rec}
    return render_template('audit.html', result=result)

@app.route('/pulse', methods=['GET', 'POST'])
def pulse():
    result = None
    if request.method == 'POST':
        platform = request.form.get('platform', '')
        tone = request.form.get('tone', '')
        goal = request.form.get('goal', '')
        idea = request.form.get('idea', '').strip()
        if not idea:
            flash('Write your content idea first.', 'danger')
        else:
            a, t, co, r = (50, 55, 45, 25)
            if platform == 'Instagram':
                a += 14
            if platform == 'LinkedIn':
                t += 12
            if platform == 'YouTube':
                a += 10
            if tone == 'Storytelling':
                a += 10
                t += 6
            if tone == 'Educational':
                t += 12
            if tone == 'Bold':
                a += 10
                r += 8
            if goal == 'Leads':
                co += 18
            if goal == 'Sales':
                co += 15
                r += 5
            if len(idea) > 80:
                t += 5
            if any((w in idea.lower() for w in ['free', 'offer', 'discount'])):
                co += 8
                r += 5
            if '?' in idea:
                a += 5
            a = min(98, a + random.randint(-3, 5))
            t = min(98, t + random.randint(-3, 5))
            co = min(98, co + random.randint(-3, 5))
            r = max(5, min(90, r + random.randint(-2, 4)))
            rec = 'Strong concept. Add one proof point and a single CTA before publishing.' if r <= 50 else 'Good attention potential, but reduce sales pressure and add proof or value.'
            c = db()
            c.execute('INSERT INTO simulations(user_id,platform,tone,goal,idea,attention,trust,conversion,risk,recommendation,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (session.get('uid'), platform, tone, goal, idea, a, t, co, r, rec, datetime.now().isoformat(timespec='seconds')))
            c.commit()
            c.close()
            result = {'attention': a, 'trust': t, 'conversion': co, 'risk': r, 'recommendation': rec}
    return render_template('pulse.html', result=result)

@app.route('/dna', methods=['GET', 'POST'])
def dna():
    result = None
    if request.method == 'POST':
        brand = request.form.get('brand_name', '').strip()
        tone = request.form.get('tone', '')
        colors = request.form.get('colors', '').strip()
        keywords = request.form.get('keywords', '').strip()
        idea = request.form.get('idea', '').strip()
        if not all([brand, tone, colors, keywords, idea]):
            flash('Complete every Brand DNA field.', 'danger')
        else:
            terms = [x.strip().lower() for x in keywords.split(',') if x.strip()]
            hits = sum((1 for x in terms if x in idea.lower()))
            score = min(96, 52 + min(28, hits * 7) + (8 if tone.lower() in idea.lower() else 0) + (4 if len(colors) > 8 else 0))
            rec = 'High DNA match: the idea sounds like the same brand.' if score >= 80 else 'Medium DNA match: add 1–2 brand keywords to make recognition stronger.'
            c = db()
            c.execute('INSERT INTO dna_checks(user_id,brand_name,tone,colors,keywords,idea,score,recommendation,created_at) VALUES(?,?,?,?,?,?,?,?,?)', (session.get('uid'), brand, tone, colors, keywords, idea, score, rec, datetime.now().isoformat(timespec='seconds')))
            c.commit()
            c.close()
            result = {'score': score, 'recommendation': rec}
    return render_template('dna.html', result=result)

@app.route('/mood', methods=['GET', 'POST'])
def mood():
    result = None
    if request.method == 'POST':
        brand = request.form.get('brand_name', '').strip()
        mood_choice = request.form.get('mood', '').strip()
        goal = request.form.get('goal', '').strip()
        audience = request.form.get('audience', '').strip()
        if not all([brand, mood_choice, goal, audience]):
            flash('Complete every Brand Mood field.', 'danger')
        else:
            mood_map = {
                'Professional': {
                    'style': 'Clean layouts, structured spacing, confident typography and proof-focused visuals.',
                    'content': 'Use practical tips, results, case studies and clear calls to action.',
                },
                'Luxury': {
                    'style': 'Minimal layouts, generous whitespace, refined typography and premium product imagery.',
                    'content': 'Use fewer words, strong visuals, exclusivity and quality-focused storytelling.',
                },
                'Friendly': {
                    'style': 'Warm language, rounded shapes, approachable visuals and conversational design.',
                    'content': 'Use relatable stories, community questions and human behind-the-scenes content.',
                },
                'Youthful': {
                    'style': 'Energetic layouts, short copy, playful shapes and quick visual hooks.',
                    'content': 'Use trends carefully, short-form ideas, polls and interactive content.',
                },
                'Minimal': {
                    'style': 'Simple grids, limited visual elements, strong hierarchy and plenty of breathing room.',
                    'content': 'Use concise educational posts, focused messages and one clear CTA.',
                },
                'Bold': {
                    'style': 'High-contrast typography, strong headlines, confident compositions and decisive CTAs.',
                    'content': 'Use opinion-led posts, strong hooks, comparisons and action-oriented campaigns.',
                },
            }
            profile = mood_map.get(mood_choice, mood_map['Professional'])
            score = 70
            if goal in ['Sales', 'Leads']:
                score += 8
            if len(audience) >= 25:
                score += 8
            if mood_choice in ['Professional', 'Minimal', 'Luxury'] and goal == 'Awareness':
                score += 5
            if mood_choice in ['Friendly', 'Youthful'] and goal == 'Engagement':
                score += 7
            score = min(96, score)
            result = {'brand': brand, 'mood': mood_choice, 'goal': goal, 'score': score, 'style': profile['style'], 'content': profile['content']}
            c = db()
            c.execute('INSERT INTO mood_checks\n                (user_id, brand_name, mood, goal, audience, score, style_direction, content_direction, created_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (session.get('uid'), brand, mood_choice, goal, audience, score, profile['style'], profile['content'], datetime.now().isoformat(timespec='seconds')))
            c.commit()
            c.close()
    return render_template('mood.html', result=result)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        msg = request.form.get('message', '').strip()
        if not name or not email or (not msg):
            flash('Fill all contact fields.', 'danger')
        else:
            c = db()
            c.execute('INSERT INTO chats(user_id,name,email,message,created_at) VALUES(?,?,?,?,?)', (session.get('uid'), name, email, msg, datetime.now().isoformat(timespec='seconds')))
            c.commit()
            c.close()
            flash('Message sent. You can see replies in your dashboard.', 'success')
            return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not need_login():
        return redirect(url_for('login'))
    u = user()
    msg = request.form.get('message', '').strip()
    if msg:
        c = db()
        c.execute('INSERT INTO chats(user_id,name,email,message,created_at) VALUES(?,?,?,?,?)', (u['id'], u['name'], u['email'], msg, datetime.now().isoformat(timespec='seconds')))
        c.commit()
        c.close()
        flash('Message sent to BrandBoost support.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    connection = db()
    stats = {
        'users': connection.execute(
            "SELECT COUNT(*) n FROM users WHERE role='user'"
        ).fetchone()['n'],
        'orders': connection.execute(
            'SELECT COUNT(*) n FROM orders'
        ).fetchone()['n'],
        'revenue': connection.execute(
            "SELECT COALESCE(SUM(amount), 0) n FROM orders WHERE status='Paid'"
        ).fetchone()['n'],
        'demo_orders': connection.execute(
            "SELECT COUNT(*) n FROM orders WHERE status LIKE 'Demo Confirmed%'"
        ).fetchone()['n'],
        'leads': connection.execute(
            'SELECT COUNT(*) n FROM chats'
        ).fetchone()['n'],
        'audits': connection.execute(
            'SELECT COUNT(*) n FROM audits'
        ).fetchone()['n'],
        'simulations': connection.execute(
            'SELECT COUNT(*) n FROM simulations'
        ).fetchone()['n'],
        'dna_checks': connection.execute(
            'SELECT COUNT(*) n FROM dna_checks'
        ).fetchone()['n'],
        'mood_checks': connection.execute(
            'SELECT COUNT(*) n FROM mood_checks'
        ).fetchone()['n'],
    }
    orders = connection.execute('SELECT orders.*, users.name, users.email\n           FROM orders LEFT JOIN users ON users.id=orders.user_id\n           ORDER BY orders.id DESC LIMIT 50').fetchall()
    chats = connection.execute('SELECT * FROM chats ORDER BY id DESC LIMIT 50').fetchall()
    users = connection.execute('SELECT id, name, email, role, trial_started, created_at FROM users ORDER BY id DESC').fetchall()
    connection.close()
    return render_template('admin.html', stats=stats, orders=orders, chats=chats, users=users)

@app.route('/admin/data')
def admin_data():
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))
    connection = db()
    data = {
        'audits': connection.execute(
            """SELECT audits.*, users.name AS user_name,
                      users.email AS user_email
               FROM audits
               LEFT JOIN users ON users.id = audits.user_id
               ORDER BY audits.id DESC"""
        ).fetchall(),
        'simulations': connection.execute(
            """SELECT simulations.*, users.name AS user_name,
                      users.email AS user_email
               FROM simulations
               LEFT JOIN users ON users.id = simulations.user_id
               ORDER BY simulations.id DESC"""
        ).fetchall(),
        'dna_checks': connection.execute(
            """SELECT dna_checks.*, users.name AS user_name,
                      users.email AS user_email
               FROM dna_checks
               LEFT JOIN users ON users.id = dna_checks.user_id
               ORDER BY dna_checks.id DESC"""
        ).fetchall(),
        'mood_checks': connection.execute(
            """SELECT mood_checks.*, users.name AS user_name,
                      users.email AS user_email
               FROM mood_checks
               LEFT JOIN users ON users.id = mood_checks.user_id
               ORDER BY mood_checks.id DESC"""
        ).fetchall(),
        'orders': connection.execute(
            """SELECT orders.*, users.name AS user_name,
                      users.email AS user_email
               FROM orders
               LEFT JOIN users ON users.id = orders.user_id
               ORDER BY orders.id DESC"""
        ).fetchall(),
        'chats': connection.execute(
            'SELECT * FROM chats ORDER BY id DESC'
        ).fetchall(),
    }
    connection.close()
    return render_template('admin_data.html', data=data)

@app.route('/admin/reply/<int:cid>', methods=['POST'])
def admin_reply(cid):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    reply = request.form.get('reply', '').strip()
    c = db()
    c.execute('UPDATE chats SET reply=?,status="Replied" WHERE id=?', (reply, cid))
    c.commit()
    c.close()
    flash('Customer reply saved.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/appearance', methods=['GET', 'POST'])
def admin_appearance():
    """Let the administrator edit live site text and visual appearance."""
    if session.get('role') != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action', 'save')
        if action == 'generate':
            style = request.form.get('style_name', 'Modern & Creative')
            palettes = {
                'Modern & Creative': ('#6d4aff', '#1c9a67'),
                'Luxury & Premium': ('#7a5528', '#d6b56d'),
                'Friendly & Warm': ('#e76f51', '#2a9d8f'),
                'Youthful & Energetic': ('#e83e8c', '#ff9f1c'),
                'Minimal & Calm': ('#475569', '#0f766e'),
                'Bold & Powerful': ('#c1121f', '#fca311'),
                'Nature & Wellness': ('#287a4b', '#c28b36'),
                'Technology & Trust': ('#2457c5', '#00a6a6'),
            }
            primary, accent = palettes.get(style, palettes['Modern & Creative'])
            connection = db()
            connection.executemany(
                'INSERT INTO site_settings(setting_key, setting_value) VALUES (?, ?) '
                'ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value',
                [('style_name', style), ('primary_color', primary), ('accent_color', accent)],
            )
            connection.commit()
            connection.close()
            flash(f'Automatic branding applied: {style}. The website colours have been updated.', 'success')
            return redirect(url_for('admin_appearance'))

        allowed = ['site_name', 'tagline', 'hero_title', 'hero_text', 'primary_color', 'accent_color']
        updates = []
        for key in allowed:
            value = request.form.get(key, '').strip()
            if key in ('primary_color', 'accent_color'):
                if len(value) != 7 or not value.startswith('#') or any(ch not in '0123456789abcdefABCDEF' for ch in value[1:]):
                    flash('Please enter valid hex colours, for example #6d4aff.', 'danger')
                    return redirect(url_for('admin_appearance'))
            if not value:
                flash('Website settings cannot be left empty.', 'danger')
                return redirect(url_for('admin_appearance'))
            updates.append((key, value))
        connection = db()
        connection.executemany(
            'INSERT INTO site_settings(setting_key, setting_value) VALUES (?, ?) '
            'ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value',
            updates,
        )
        connection.commit()
        connection.close()
        flash('Website content and appearance saved successfully.', 'success')
        return redirect(url_for('admin_appearance'))

    return render_template('admin_appearance.html', settings=get_site_settings())


@app.route('/api/health')
def health():
    return jsonify(status='ok', database='SQLite connected', service='BrandBoost')

@app.errorhandler(404)
def e404(e):
    return (render_template('404.html'), 404)
init_db()
if __name__ == '__main__':
    app.run(debug=True)
