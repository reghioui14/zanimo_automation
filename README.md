# Zanimo Automation

Automatisation marketing et relation client pour la plateforme e-commerce **Zanimo**, développée dans le cadre d'un PFA (Sogeplan). Le système repose sur trois workflows n8n :

## 1. Génération de visuels publicitaires
Automatise la création de visuels publicitaires personnalisés pour les produits Zanimo, sans ressaisie manuelle à chaque génération.

- déclenchement quotidien automatique (sélection aléatoire d'un produit) ou manuel via formulaire (lien produit + promotion + tagline) ;
- extraction des données produit depuis Zanimo.tn ;
- génération d'une scène publicitaire par IA (Cloudflare Workers AI) ;
- détourage et composition du produit réel sur la scène (rembg) ;
- ajout d'un badge promo ou d'une tagline marketing ;
- diffusion automatique sur WhatsApp.

## 2. Email de bienvenue et fidélisation
Automatise l'envoi d'un email de bienvenue aux nouveaux clients, avec sauvegarde de leurs données pour une analyse future.

- détection des nouveaux clients ;
- envoi d'un email personnalisé via Brevo (présentation du programme de fidélité) ;
- sauvegarde des données client (CSV) pour analyse future.

## 3. Gestion centralisée des erreurs
Système centralisé de gestion et de notification des erreurs pour les deux automatisations précédentes.

- détection automatique des échecs (WhatsApp, IA, scraping, email) ;
- classification de la cause probable ;
- notification par email à l'administrateur.

## Stack technique
n8n · Docker · Python / FastAPI · Cloudflare Workers AI · rembg · BeautifulSoup · SQLite · PostgreSQL · Brevo · Evolution API (WhatsApp)

## Structure du repo