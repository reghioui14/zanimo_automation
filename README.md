# Invoice AI

Invoices are read by AI, validated, stored in PostgreSQL, and reviewed in a small web dashboard.

## Structure

- `workflows/`: n8n workflows (JSON). Extraction, validation, database insert, and the AI chat.
- `streamlit/`: small web interface to browse invoices and ask questions in a chat.
- `.env.example`: template for environment variables.

## Setup

1. Copy `.env.example` to `.env` and fill in your own passwords.
2. Start the stack: `docker compose up -d`
3. Import the files from `workflows/` into n8n and recreate the credentials (Gemini, PostgreSQL, IMAP).

## Database

| Table | Main columns |
|---|---|
| `vendors` | `id`, `name` (unique), `created_at` |
| `invoices` | `id`, `vendor_id`, `invoice_number`, `invoice_date`, `currency`, `total_amount`, `confidence_score`, `status`, `validation_reason`, `payment_status`, `paid_at`, `original_file_path`, `created_at` |
| `line_items` | `id`, `invoice_id`, `description`, `quantity`, `unit_price` |
| `corrections` | `id`, `invoice_id`, `field_name`, `old_value`, `new_value`, `corrected_by`, `corrected_at` |

```
vendors 1 ── * invoices 1 ── * line_items
                    1 ── * corrections
```

- `status`: `auto_approved`, `approved` or `flagged` (default `flagged`)
- `payment_status`: `paid` or `unpaid` (default `unpaid`)
- Deleting a vendor or an invoice also deletes the rows that depend on it.

Deux choses vues dans ton schéma :

ON DELETE CASCADE : supprimer un fournisseur supprime ses factures, leurs lignes et leurs corrections. J’ai gardé la phrase dans le README, mais c’est un comportement à connaître.
La clé étrangère de invoices vers vendors apparaît dans ton affichage de vendors (section « Referenced by »), donc le schéma du README est correct.

# Zanimo Automation

Automatisation marketing et relation client pour la plateforme e-commerce **Zanimo** . Le système repose sur trois workflows n8n :

## 1. Génération de visuels publicitaires
Automatise la création de visuels publicitaires personnalisés pour les produits Zanimo, sans ressaisie manuelle à chaque génération.

déclenchement quotidien automatique (sélection aléatoire d'un produit) ou manuel via formulaire (lien produit + promotion + tagline) ;
extraction des données produit depuis Zanimo.tn ;
génération d'une scène publicitaire par IA (Cloudflare Workers AI) ;
détourage et composition du produit réel sur la scène (rembg) ;
ajout d'un badge promo ou d'une tagline marketing ;
diffusion automatique sur WhatsApp.

## 2. Email de bienvenue et fidélisation
Automatise l'envoi d'un email de bienvenue aux nouveaux clients, avec sauvegarde de leurs données pour une analyse future.

détection des nouveaux clients ;
envoi d'un email personnalisé via Brevo (présentation du programme de fidélité) ;
sauvegarde des données client (CSV) pour analyse future.

## 3. Gestion centralisée des erreurs
Système centralisé de gestion et de notification des erreurs pour les deux automatisations précédentes.

détection automatique des échecs (WhatsApp, IA, scraping, email) ;
classification de la cause probable ;
notification par email à l'administrateur.

## Stack technique
n8n · Docker · Python / FastAPI · Cloudflare Workers AI · rembg · BeautifulSoup · SQLite · PostgreSQL · Brevo · Evolution API (WhatsApp)

## Structure du repo

regenera ca aussi en anglai

Rewriting the Zanimo README in English.
markdown
# Zanimo Automation

Marketing and customer relationship automation for the **Zanimo** e-commerce platform. The system relies on three n8n workflows:

## 1. Advertising visual generation
Automates the creation of custom advertising visuals for Zanimo products, with no manual re-entry for each generation.

- daily automatic trigger (random product selection) or manual trigger through a form (product link + promotion + tagline);
- product data extraction from Zanimo.tn;
- AI-generated advertising scene (Cloudflare Workers AI);
- background removal and compositing of the real product onto the scene (rembg);
- promo badge or marketing tagline overlay;
- automatic distribution on WhatsApp.

## 2. Welcome email and customer loyalty
Automates sending a welcome email to new customers, and saves their data for future analysis.

- new customer detection;
- personalized email sent through Brevo (loyalty program presentation);
- customer data saved to CSV for future analysis.

## 3. Centralized error handling
A centralized error handling and notification system shared by the two workflows above.

- automatic detection of failures (WhatsApp, AI, scraping, email);
- classification of the probable cause;
- email notification to the administrator.

## Tech stack
n8n · Docker · Python / FastAPI · Cloudflare Workers AI · rembg · BeautifulSoup · SQLite · PostgreSQL · Brevo · Evolution API (WhatsApp)
