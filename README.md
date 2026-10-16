# BrandBoost - Complete Social Media Branding Project

## Run the project

Open this folder in VS Code. The terminal must be inside the folder containing `app.py` and `requirements.txt`.

Install the dependencies:

```powershell
py -m pip install -r requirements.txt
```

Start the Flask backend:

```powershell
py app.py
```

Then open `http://127.0.0.1:5000` in your browser.

The SQLite database is created automatically when the application starts.

## Admin demo

Email: `admin@brandboost.local`

Password: `admin123`

## Features

- User registration and login
- SQLite database
- Free brand audit
- 7-day free trial
- Starter, Growth and Pro packages
- Value-added offers
- Demo order flow
- Customer dashboard
- Customer-to-admin chat
- Admin dashboard
- Brand Pulse Simulator
- Brand DNA Check
- Responsive frontend


## Final showcase features

- Premium responsive visual layer with animated gradients, hover effects and polished cards
- Brand Pulse Simulator
- Brand DNA Check
- Brand Mood Studio — a rule-based brand-personality planner that converts a chosen mood into visual and content direction
- Free audit and 7-day trial
- Starter package at ₹399 plus Growth and Pro plans
- Value-added offers designed as digital bonuses rather than large discounts
- Customer chat stored in SQLite and replyable from Admin
- Admin dashboard with customer, order and message data

## Demo flow

1. Open the homepage.
2. Show Services and the unique-feature cards.
3. Open Brand Mood Studio and generate a mood profile.
4. Open Brand Pulse and test a campaign idea.
5. Open Pricing and show the Free Trial, ₹399 Starter, Growth and Pro offers.
6. Register a normal customer account.
7. Activate the Free Trial or select a package.
8. Open Dashboard and send a customer message.
9. Log in as admin using the demo credentials and reply to the message.
10. Open `/api/health` to demonstrate the backend/database health endpoint.


## Payment and saved-data improvements

- Customer dashboard now includes saved order, audit, Brand Pulse, Brand DNA, Brand Mood, and support-message history.
- Admin dashboard includes counts for stored tool results and a **View All Saved Data** page at `/admin/data`. The page shows all stored audits, Pulse tests, DNA checks, Mood checks, orders, and support messages.
- Demo orders are clearly marked **Demo Confirmed - Not Paid**. They are not included in verified revenue.
- Optional Razorpay Checkout support is included. To enable gateway checkout, install dependencies and set these environment variables before starting the app: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `BRANDBOOST_SECRET_KEY`. Use Razorpay **test** keys for development and verify your account settings before live use. Do not put the secret key in HTML or share it. Without gateway keys, the site provides a classroom demo checkout that stores an unpaid demo order only.

### Run locally

```bash
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The SQLite database `brandboost.db` is created beside `app.py`. Admin demo login: `admin@brandboost.local` / `admin123`. Change demo credentials and the secret key before any public deployment.

**Important:** Pulse, DNA, Audit, and Mood scores are rule-based project demonstrations, not actual AI predictions or live social-platform analytics. Real payment processing only becomes available after you configure your own Razorpay account keys.


### Example environment setup (Windows PowerShell)

Use your own Razorpay **test** credentials from your Razorpay dashboard. Replace the example values; do not copy them literally. Run these in the same terminal before `py app.py`:

```powershell
$env:BRANDBOOST_SECRET_KEY = "replace-with-a-long-random-secret"
$env:RAZORPAY_KEY_ID = "rzp_test_your_key_id"
$env:RAZORPAY_KEY_SECRET = "your_test_secret"
py app.py
```

Without these gateway variables, the app intentionally stays in demo-checkout mode. For live payments, complete Razorpay account verification, use live credentials securely on the server, configure HTTPS and review applicable payment, privacy, and tax requirements.


## Admin automatic branding and website editor

Sign in with the administrator account, then open **Admin → Edit Website Appearance** (route `/admin/appearance`).

- **Python automatic branding:** choose a brand personality and the backend applies a matching primary/accent colour palette.
- **Website content editor:** change the website name, footer tagline, homepage headline, homepage description, and colours.
- **Persistent settings:** site settings are saved in the SQLite `site_settings` table and remain after restart.
- **Access control:** the editor is restricted to an authenticated administrator.

The palette generator is rule-based Python logic; it does not require an AI API.
