# Zanimo Automation

Marketing and customer relationship automation for the **Zanimo** e-commerce platform. The system is built on three n8n workflows:

## 1. Advertising visual generation
Automates the creation of personalized advertising visuals for Zanimo products, with no manual re-entry for each generation.

- automatic daily trigger (random product selection) or manual trigger via form (product link + promotion + tagline);
- product data extraction from Zanimo.tn;
- AI-generated advertising scene (Cloudflare Workers AI);
- background removal and compositing of the real product onto the scene (rembg);
- addition of a promo badge or marketing tagline;
- automatic distribution on WhatsApp.

## 2. Welcome email and customer loyalty
Automates sending a welcome email to new customers, while saving their data for future analysis.

- detection of new customers;
- personalized email sent via Brevo (loyalty program presentation);
- customer data saved (CSV) for future analysis.

## 3. Centralized error handling
Centralized error handling and notification system for the two previous automations.

- automatic detection of failures (WhatsApp, AI, scraping, email);
- classification of the probable cause;
- email notification to the administrator.

## Tech stack
n8n · Docker · Python / FastAPI · Cloudflare Workers AI · rembg · BeautifulSoup · SQLite · PostgreSQL · Brevo · Evolution API (WhatsApp)

## Repository structure
