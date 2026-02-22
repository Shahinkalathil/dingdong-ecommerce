# 🕰️ DINGDONG — Watch E-Commerce Platform

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python) ![Django](https://img.shields.io/badge/Django-MVC-green?logo=django) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?logo=postgresql) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-In%20Development-orange)

> *"Time is a Luxury"* — A classic collection of luxury watches for the real generation.

---

## 📖 Description

**DINGDONG** is a full-stack e-commerce web application built with Python Django (MVC architecture) for a boutique watch brand. The name is inspired by the timeless ding-dong chime of classic mechanical clocks — symbolizing precision, rhythm, and enduring design.

The platform is designed to support small and local watch brands by providing a digital storefront to reach a wider audience. It delivers a clean, scalable, and secure shopping experience covering the complete product journey — from browsing to checkout.

This project was built as a real-world full-stack application covering UI/UX design, database modeling, and backend development.

---

## 📚 Table of Contents

- [Description](#-description)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Tests](#-tests)
- [Project Status](#-project-status)
- [Authors & Acknowledgments](#-authors--acknowledgments)
- [License](#-license)

---

## ✨ Features

### 👤 User Side
| Module | Features |
|---|---|
| 🔐 Authentication | Sign up, Login, Logout, Email OTP Verification, Forgot/Reset Password via token link |
| ⌚ Products | Browse by brand, category, color variants, images, and pricing |
| 🛒 Cart & Wishlist | Add/remove items, quantity management, real-time cart updates |
| 💳 Checkout & Payments | Razorpay online payment, Cash on Delivery (COD), Wallet payment |
| 📦 Order Flow | Order placement, tracking, order history, returns, and downloadable invoices |
| 👤 Profile Management | Edit profile, manage multiple addresses, wallet balance, password reset |

### 🛠️ Admin Side
| Module | Features |
|---|---|
| 📊 Dashboard | Sales overview, order statistics, key metrics, downloadable reports |
| 👥 User Management | View, block/unblock users, manage user activity |
| 📦 Product Management | Add, edit, list/unlist products with variants and images |
| 🏷️ Brand & Category Management | Manage watch brands and product categories |
| 🚚 Order Management | View orders, update status, handle returns and refunds |
| 🎁 Offer Management | Create product-level and brand-level offers |
| 🎟️ Coupon Management | Create and apply discount coupons |
| 👛 Wallet Management | Manage user wallet transactions and balances |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Django (MVC) |
| Templating | Jinja2 / Django Templates |
| Frontend | HTML5, CSS3, JavaScript, Tailwind CSS |
| Database | PostgreSQL |
| Payment Gateway | Razorpay |
| Authentication | Django Allauth, Custom OTP |
| Version Control | Git & GitHub |
| Design | Figma, DrawSQL |

---

## 📁 Project Structure

```
DINGDONG/
├── Server/                  # Project settings, URLs, WSGI/ASGI
├── authentication/          # Login, signup, OTP, password reset
├── brands/                  # Watch brand management
├── cart/                    # Cart and cart items
├── categories/              # Product categories
├── checkout/                # Checkout flow and address handling
├── coupons/                 # Discount coupon logic
├── dashboard/               # Admin dashboard and analytics
├── home/                    # Homepage views and banners
├── offers/                  # Product and brand offers
├── orders/                  # Order placement, tracking, returns
├── products/                # Product listings, variants, images
├── profiles/                # User profile and address management
├── user/                    # User model and admin views
├── wallet/                  # Wallet and transaction management
├── wishlist/                # Wishlist functionality
├── template/
│   ├── admin_panel/         # Admin-side HTML templates
│   └── user_side/           # User-facing HTML templates
├── media/                   # Uploaded images (products, brands, banners)
├── static/                  # CSS, JS, and static assets
├── manage.py
└── requirements.txt
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.10+
- PostgreSQL
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/dingdong.git
   cd dingdong
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the root directory and add:
   ```env
	SECRET_KEY=django-insecure-3oos!cdz=^^3@yb8(yt1+08k*^225eh@cuylm)&l8+0f_kjr0u

	# Email Configuration
	EMAIL_HOST_USER=shahinluttu@gmail.com
	EMAIL_HOST_PASSWORD=jstz sivc nwls ytnw

	# Database Configuration
	DB_NAME=mydbdingdong
	DB_USER=dong_user
	DB_PASSWORD=shahin1212
	DB_HOST=localhost
	DB_PORT=5432

	# Site Configuration
	USE_NGROK=0
	SITE_ID_LOCAL=6
	SITE_ID_NGROK=5

	# Google OAuth Configuration
	GOOGLE_CLIENT_ID=803453159842-qenjn7nbfsflffdtgvfpm6jat3f37ca7.apps.googleusercontent.com
	GOOGLE_CLIENT_SECRET=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
	GOOGLE_REDIRECT_URI=http://localhost:8000/accounts/google/login/callback/
	GOOGLE_REDIRECT_URI_NGROK=https://223bd8012b44.ngrok-free.app/accounts/google/login/callback/


	# Razorpay TEST Configuration
	RAZORPAY_KEY_ID=rzp_test_S44MxPSsgVJtze
	RAZORPAY_KEY_SECRET=glnxh28zDOkfPiuuciBCKt84
   ```

5. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000` in your browser.

---

## 🚀 Usage

- **User side:** Visit the homepage, browse watches by brand or category, add items to cart or wishlist, and complete checkout using Razorpay, COD, or your wallet.
- **Admin panel:** Navigate to `/admin-panel/` to manage products, users, orders, coupons, offers, and view the sales dashboard.

---

## 🧪 Tests

Each Django app includes a `tests.py` file. To run all tests:

```bash
python manage.py test
```

To run tests for a specific app:

```bash
python manage.py test authentication
python manage.py test orders
```

---

## 📌 Project Status

🟡 **In Development** — Core features are complete and functional. The following enhancements are planned:

- Improve UI/UX and responsiveness
- Add advanced analytics and sales reports
- Enhance security and performance optimizations
- Deploy to production (AWS / Railway / Render)

---

## 👨‍💻 Authors & Acknowledgments

**Shahin KalathiL**
- 📧 shahinoffical.se@gmail.com
- 🌐 [www.shahinkalathi.l.com](http://www.shahinkalathi.l.com)
- 🔗 [LinkedIn](https://www.linkedin.com/in/shahin-kalathi-l-b25664353/)
- 📍 Ponnani, Malappuram, Kerala, India

Special thanks to the open-source community and the Django documentation for making this project possible.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

> You are free to use, modify, and distribute this project with attribution. For more help choosing a license, visit [choosealicense.com](https://choosealicense.com).