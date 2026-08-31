"""Storage delle foto caricate dagli utenti (RF-06/RF-08b) — astratto
dietro un'interfaccia (stesso pattern di services/email_provider.py e
services/content_moderation.py) così l'endpoint di upload non dipende da
un backend specifico.

Perché esiste: il disco del piano gratuito Render è EFFIMERO — ogni
redeploy sostituisce il container e cancella tutto ciò che non è nel
repo git. Il pool demo era già stato migrato su R2 una tantum
(scripts/seed_render_from_local.py), ma l'endpoint di upload LIVE
scriveva ancora solo su disco locale: una foto caricata da un utente
reale spariva al primo redeploy successivo (trovato dal vivo il
2026-08-31 su un account di test reale, v. CLAUDE.md).

Selezione automatica: se le credenziali R2 sono presenti nell'ambiente,
le usa; altrimenti fallback su disco locale (comportamento invariato per
lo sviluppo locale, dove il disco non è effimero e non servono credenziali
R2)."""

import os
from abc import ABC, abstractmethod
from uuid import UUID

from fastapi import UploadFile


class PhotoStorage(ABC):
    @abstractmethod
    def salva(self, user_id: UUID, sottocartella: str, file: UploadFile) -> str:
        """Salva il file e ritorna il valore da scrivere in
        foto_profilo_url/foto_partner_ideale_url — un path relativo
        (storage locale, servito da /photos/) o un URL assoluto (R2)."""
        raise NotImplementedError


class LocalPhotoStorage(PhotoStorage):
    def __init__(self, storage_dir: str):
        self._storage_dir = storage_dir

    def salva(self, user_id: UUID, sottocartella: str, file: UploadFile) -> str:
        import shutil

        os.makedirs(os.path.join(self._storage_dir, sottocartella), exist_ok=True)
        estensione = os.path.splitext(file.filename or "")[1] or ".jpg"
        nome_file = f"{user_id}{estensione}"
        percorso_assoluto = os.path.join(self._storage_dir, sottocartella, nome_file)
        with open(percorso_assoluto, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return f"{sottocartella}/{nome_file}"


class R2PhotoStorage(PhotoStorage):
    def __init__(self):
        import boto3

        self._bucket = os.environ["R2_BUCKET_NAME"]
        self._public_base = os.environ["R2_PUBLIC_BASE_URL"].rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )

    def salva(self, user_id: UUID, sottocartella: str, file: UploadFile) -> str:
        estensione = os.path.splitext(file.filename or "")[1] or ".jpg"
        chiave = f"{sottocartella}/{user_id}{estensione}"
        self._client.upload_fileobj(
            file.file, self._bucket, chiave,
            ExtraArgs={"ContentType": file.content_type or "image/jpeg"},
        )
        return f"{self._public_base}/{chiave}"


_storage: PhotoStorage | None = None


def get_photo_storage(storage_dir: str) -> PhotoStorage:
    global _storage
    if _storage is None:
        if os.environ.get("R2_BUCKET_NAME"):
            _storage = R2PhotoStorage()
        else:
            _storage = LocalPhotoStorage(storage_dir)
    return _storage
