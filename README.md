# Healthcare Project
AI-Powered Wellness Platform built with Django & GPT  

> Personal fitness, diet, routine, music, and AI health coach in one integrated platform.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.x-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📌 Table of Contents

- [Overview](#overview)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [System Architecture](#-system-architecture)
- [Setup & Running](#-setup--running)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

5team-Project is a comprehensive **AI-powered wellness platform** built with Django.  
It integrates fitness routines, diet tracking, music recommendation, place search, e-commerce,  
and an interactive AI health coach into a single modular system.

The platform is designed as a **multi-app Django architecture**,  
where each domain operates independently while sharing:

- Unified user profile
- Centralized achievement system
- AI-powered personalization layer

This project focuses on combining **software engineering**, **AI services**,  
and **gamification** to encourage sustainable healthy habits.

---

## ✨ Key Features

### 👤 User & Account
- Registration, login, and profile management  
- Multi-language support (Korean / English / Spanish)  
- Health profile: height, weight, target weight  

### 🏆 Achievement System
- Centralized achievement engine across all modules  
- Streaks, milestones, and AI interaction rewards  
- Titles & badges for long-term engagement  

### 🤖 AI Chatbot & Health Coach
- GPT-4-O powered conversational agent  
- Retrieval-Augmented Generation (RAG) with FAISS  
- File & image understanding (PDF, CSV, image)  
- Product recommendation via Coupang API  
- DALL-E image generation  
- Automatic achievement rewards for interactions  

### 🥗 Diet & Nutrition
- Meal logging with photo upload  
- AI-based nutrition analysis  
- Daily / weekly intake summaries  
- Diet streak & balance achievements  

### 🏋️ Routine & Workout
- Manual routine builder  
- GPT-generated workout plans  
- Workout logging & streak tracking  
- AI routine feedback and translation  

### 🎵 Music & Place
- Personalized music keyword generation via GPT  
- YouTube-based playlist search  
- Kakao Map powered place search  
- Search diversity & time-based achievements  

### 🛒 Store & Body Analysis
- Brand filtering, favorites, and reviews  
- AI-based body shape analysis  
- Fashion & training tips  
- Auto-generated brand descriptions & tags via GPT  

### 📊 Dashboard & Health Metrics
- Integrated service dashboard  
- Weight / muscle / fat charts  
- Latest routine & diet summary  
- Achievement overview  

---

## 🛠 Technology Stack

**Backend**
- Django & Django REST Framework (Python 3.11)  
- PostgreSQL / SQLite (development)  
- Redis (optional caching)  

**AI & Data**
- OpenAI GPT-4-O, GPT-4-O-Mini  
- LangChain + FAISS (RAG pipeline)  
- DALL-E (image generation)  

**Frontend**
- Django Templates  
- Bootstrap & Tailwind CSS  
- JavaScript (AJAX, charts, filtering)  

**External APIs**
- Kakao Map API (place search)  
- YouTube API (music search)  
- Coupang API (product recommendation)  

---

## 📂 Project Structure

```bash
5team-project/
├── Steam-project/     # Main Django project (settings, urls, wsgi/asgi)
├── accounts/          # User management & authentication
├── achievements/     # Central achievement engine
├── chatbot/          # AI health coach & RAG system
├── diet/             # Diet logging & nutrition analysis
├── routine/          # Workout routines & logs
├── music/            # Music recommendation module
├── place/            # Place search (Kakao Map)
├── store/            # E-commerce & body analysis
├── web/              # Main site & dashboard views
├── config/           # Environment & configuration
├── locale/           # Django i18n files
├── locales/          # JSON translations (KO / EN / ES)
├── media/            # Uploaded files
├── staticfiles/      # Collected static files
├── assets/           # Frontend assets
