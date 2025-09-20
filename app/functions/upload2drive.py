from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from core.config import SERVICE_ACCOUNT_KEY


class UploadToDrive:
    SCOPES = [
        "https://www.googleapis.com/auth/drive.file",
    ]

    @staticmethod
    def upload_audio(file_path: Path, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload an audio file to Google Drive. Returns file metadata with links."""
        path = Path(file_path)
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Audio file missing or empty: {path}")

        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY, scopes=UploadToDrive.SCOPES)
        drive_service = build("drive", "v3", credentials=credentials)

        file_metadata: Dict[str, Any] = {"name": path.name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        mime = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/wav"
        media = MediaFileUpload(str(path), mimetype=mime, resumable=True)

        created = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink, webContentLink")
            .execute()
        )

        # Try to make the file public-readable; ignore if permission fails
        try:
            drive_service.permissions().create(
                fileId=created["id"], body={"type": "anyone", "role": "reader"}
            ).execute()
        except Exception:
            pass

        return created


