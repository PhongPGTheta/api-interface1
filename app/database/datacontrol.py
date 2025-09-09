import json
from pathlib import Path
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
DB_DIR = Path("database/DB")
SC_PATH_TODAY = DB_DIR / f"{today}_script_data.json"
AU_PATH_TODAY = DB_DIR / f"{today}_audio_data.json"
IM_PATH_TODAY = DB_DIR / f"{today}_images_data.json"
VD_PATH_TODAY = DB_DIR / f"{today}_video_data.json"

def _write_or_update(file_path_today, pattern, data, id_video):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    found = False

    for file in DB_DIR.glob(pattern):
        try:
            with open(file, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except Exception:
            all_data = []

        for i, item in enumerate(all_data):
            if item.get("id") == id_video:
                all_data[i] = data
                found = True
                with open(file, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, indent=4)
                break
        if found:
            break

    if not found:
        try:
            if file_path_today.exists():
                with open(file_path_today, "r", encoding="utf-8") as f:
                    today_data = json.load(f)
            else:
                today_data = []
        except Exception:
            today_data = []
        today_data.append(data)
        with open(file_path_today, "w", encoding="utf-8") as f:
            json.dump(today_data, f, indent=4)


def _get_data_by_uuid(pattern, uuid):
    for file in DB_DIR.glob(pattern):
        try:
            with open(file, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            for item in all_data:
                if item.get("uuid") == uuid:
                    return item
        except Exception:
            continue
    return None

class T2SModule:
    @staticmethod
    def write_or_update_data(data, id_video):
        _write_or_update(SC_PATH_TODAY, "*_script_data.json", data, id_video)

    @staticmethod
    def get_data_by_uuid(uuid):
        return _get_data_by_uuid("*_script_data.json", uuid)

class S2AModule:
    @staticmethod
    def write_or_update_data(data, id_video):
        _write_or_update(AU_PATH_TODAY, "*_audio_data.json", data, id_video)

    @staticmethod
    def get_data_by_uuid(uuid):
        return _get_data_by_uuid("*_audio_data.json", uuid)

class S2PModule:
    @staticmethod
    def write_or_update_data(data, id_video):
        _write_or_update(IM_PATH_TODAY, "*_images_data.json", data, id_video)

    @staticmethod
    def get_data_by_uuid(uuid):
        return _get_data_by_uuid("*_images_data.json", uuid)

class R2VModule:
    @staticmethod
    def write_or_update_data(data, id_video):
        _write_or_update(VD_PATH_TODAY, "*_video_data.json", data, id_video)

    @staticmethod
    def get_data_by_uuid(uuid):
        return _get_data_by_uuid("*_video_data.json", uuid)