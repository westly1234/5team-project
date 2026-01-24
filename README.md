# 5team-Project 🧠💪  
AI-Powered Wellness Platform built with Django & GPT  

> Personal fitness, diet, routine, music, and AI health coach in one platform.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.x-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 📌 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Directory Structure](#directory-structure)
- [Setup & Running](#setup--running)
- [Contributing](#contributing)
- [License](#license)

## 🧠 AI Chatbot & Health Coach

The chatbot is the core intelligence module of this platform.

**Main capabilities:**
- Retrieval-Augmented Generation (RAG) with FAISS
- Multi-language conversation (KO / EN / ES)
- File & image understanding (PDF, CSV, image)
- Product recommendation via Coupang API
- Automatic achievement rewards for interactions

## 📂 Project Structure

```bash
5team-project/
├── Steam-project/     # Main Django project
├── accounts/          # User management
├── achievements/     # Achievement engine
├── chatbot/          # AI health coach
├── diet/             # Diet logging & analysis
├── routine/          # Workout routines
├── music/            # Music recommendation
├── place/            # Place search (Kakao Map)
├── store/            # E-commerce & body analysis
├── web/              # Main site & dashboard
├── media/            # Uploaded files
├── staticfiles/      # Collected static files

## ✨ Key Features

### 👤 User & Account
- Registration, login, profile management
- Multi-language support (KO / EN / ES)
- Health profile: height, weight, target weight

### 🏆 Achievement System
- Centralized achievement engine
- Streaks, milestones, AI usage rewards
- Titles & badges across all modules

### 🤖 AI Chatbot
- GPT-4-O powered health coach
- RAG with FAISS vector store
- File & image understanding
- DALL-E image generation

### 🥗 Diet & Nutrition
- Meal logging with photo upload
- AI nutrition analysis
- Daily / weekly summaries
- Diet streak achievements

### 🏋️ Routine & Workout
- Manual routine builder
- GPT-generated workout plans
- Workout logs & streak tracking
- AI routine feedback

### 🎵 Music & Places
- Personalized music keywords
- Kakao Map place search
- Search-based achievements

### 🛒 Store & Body Analysis
- Brand filtering & recommendations
- AI body shape analysis
- Fashion & training tips

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/westly1234/5team-project.git
cd 5team-project

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python manage.py runserver

## 🧩 System Architecture

- Backend: Django (MTV pattern)
- AI Layer: LangChain + OpenAI + FAISS
- External APIs: Kakao Map, YouTube, Coupang
- Database: PostgreSQL / SQLite (dev)

The platform is designed as a modular multi-app Django architecture,  
where each domain (diet, routine, music, store, chatbot) operates independently  
but is connected through a centralized achievement and user profile system.
