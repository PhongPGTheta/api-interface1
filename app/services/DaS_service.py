import os
import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from core.config import (
    GOOGLE_API_KEY,
    DATA_AUDIO_PATH,
    DATA_TRANSCRIPT_PATH,
    DATA_IMAGEN_PATH,
    DATA_VIDEO_PATH
)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'core/config/service_account.json'

class DriveService:
    service = None

    @staticmethod
    def ConnectDrive():
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            DriveService.service = build('drive', 'v3', credentials=credentials)
            logging.info("Connected to Google Drive API successfully.")
        except Exception as e:
            logging.error(f"Failed to connect to Google Drive: {e}")

    @staticmethod
    def Load_folder(folder_name):
        try:
            service = DriveService.service
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])

            if items:
                logging.info(f"Folder '{folder_name}' found with ID: {items[0]['id']}")
                return items[0]['id']
            else:
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(body=file_metadata, fields='id').execute()
                logging.info(f"Folder '{folder_name}' created with ID: {folder['id']}")
                return folder.get('id')
        except Exception as e:
            logging.error(f"Error loading/creating folder '{folder_name}': {e}")
            return None

    class Upload_file_to_folder:
        @staticmethod
        def _upload_file(file_path, folder_id):
            try:
                service = DriveService.service
                file_name = os.path.basename(file_path)
                media = MediaFileUpload(file_path, resumable=True)
                file_metadata = {
                    'name': file_name,
                    'parents': [folder_id]
                }
                uploaded = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink'
                ).execute()
                logging.info(f"Uploaded file: {file_name}, Link: {uploaded.get('webViewLink')}")
                return uploaded.get("webViewLink")
            except Exception as e:
                logging.error(f"Failed to upload file {file_path}: {e}")
                return None

        @staticmethod
        def _Images():
            folder_id = DriveService.Load_folder("Uploaded_Images")
            return DriveService.Upload_file_to_folder._upload_files_in_directory(DATA_IMAGEN_PATH, folder_id, ['.png', '.jpg', '.jpeg', '.gif', '.bmp'])

        @staticmethod
        def _Audio():
            folder_id = DriveService.Load_folder("Uploaded_Audio")
            return DriveService.Upload_file_to_folder._upload_files_in_directory(DATA_AUDIO_PATH, folder_id, ['.mp3', '.wav', '.aac'])

        @staticmethod
        def _Video():
            folder_id = DriveService.Load_folder("Uploaded_Video")
            return DriveService.Upload_file_to_folder._upload_files_in_directory(DATA_VIDEO_PATH, folder_id, ['.mp4', '.mov', '.avi'])

        @staticmethod
        def _Script():
            folder_id = DriveService.Load_folder("Uploaded_Scripts")
            return DriveService.Upload_file_to_folder._upload_files_in_directory(DATA_TRANSCRIPT_PATH, folder_id, ['.txt', '.docx'])

        @staticmethod
        def _upload_files_in_directory(directory_path, folder_id, extensions):
            links = []
            try:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensions):
                            file_path = os.path.join(root, file)
                            link = DriveService.Upload_file_to_folder._upload_file(file_path, folder_id)
                            if link:
                                links.append(link)
            except Exception as e:
                logging.error(f"Error uploading files in {directory_path}: {e}")
            return links


class SheetService:
    @staticmethod
    def ConnectSheet():
        # Chưa triển khai - dùng gspread hoặc Google Sheets API
        logging.info("SheetService.ConnectSheet called (not implemented)")

    class SheetControl:
        @staticmethod
        def get_id_and_order():
            logging.info("SheetControl.get_id_and_order called (not implemented)")

        @staticmethod
        def update_Script_and_change_status():
            logging.info("SheetControl.update_Script_and_change_status called (not implemented)")

        @staticmethod
        def upload_link_audio():
            logging.info("SheetControl.upload_link_audio called (not implemented)")

        @staticmethod
        def upload_link_images():
            logging.info("SheetControl.upload_link_images called (not implemented)")

        @staticmethod
        def Control_checkpoint_file():
            logging.info("SheetControl.Control_checkpoint_file called (not implemented)")

        @staticmethod
        def upload_link_video():
            logging.info("SheetControl.upload_link_video called (not implemented)")
