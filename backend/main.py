"""
Ainima — API MVP (scheletro)

Copre il flusso end-to-end di Documento_Requisiti_v1.md §4: registrazione/
onboarding, profilo, preferenze, test psicometrico, matching mensile,
pagamento, scambio contatto, feedback, back-office admin.

Componenti esterni NON integrati in questo scheletro (stub espliciti nei
router, v. commenti TODO): provider OTP SMS, gateway di pagamento, chiamate
LLM per la chat-intervista EQ e la pipeline narrativa (Prompt 1-5), calcolo
embedding visivo per le foto caricate via API.

Uso: uvicorn main:app --app-dir backend --port 8010
Documentazione interattiva: http://localhost:8010/docs
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import (
    account, admin, admin_viewer, auth, contacts, engagement, feedback, matching, payments,
    preferences, profile, psychometric,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Ainima API", description="Matchmaking matrimoniale — scheletro MVP")

# Frontend Next.js gira su origin separata — necessario per le chiamate
# fetch dal browser. localhost:3000 per lo sviluppo locale, il dominio
# Netlify per il frontend di collaudo deployato (v. CLAUDE.md).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://ainima.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# storage/ è in .gitignore (contenuto caricato dagli utenti, mai
# committato) — su un clone pulito (es. Render) la cartella non esiste
# affatto, e StaticFiles pretende che esista già al momento del mount,
# altrimenti crasha subito all'avvio (trovato dal deploy reale su
# Render, v. CLAUDE.md). Le sottocartelle profilo/partner_ideale restano
# create lazy al primo upload (routers/profile.py), qui serve solo la
# cartella base.
PHOTOS_DIR = os.path.join(BASE_DIR, "storage", "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)
app.mount("/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(profile.router)
app.include_router(preferences.router)
app.include_router(psychometric.router)
app.include_router(matching.router)
app.include_router(payments.router)
app.include_router(contacts.router)
app.include_router(feedback.router)
app.include_router(engagement.router)
app.include_router(admin.router)
app.include_router(admin_viewer.router)  # viewer HTML, monta anche "/" — ultimo per non oscurare le altre rotte
