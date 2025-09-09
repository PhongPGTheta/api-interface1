HISTORY_VOICE_ID_PATH = "database/Temp/history_voice_id.json"
API_KEY = [
    {
        "name": "elevenlabsdtm@datviet.media",
        "api_key": "sk_d5d636f4f9b518dc69ec0d30cf421cfdb68d0b13e8f8b7bb"
    },
    {
        "name": "klingai.datviet",
        "api_key": "sk_ba950ea4ba9cba0e5085bdd69b3fcde807ad3c640b8e7e83"
    },
    {
        "name": "shakkerai.datviet",
        "api_key": "sk_07c3f69ec35530963c81ca6b1f53844099a5f06bb708f978"
    },
    {
        "name": "heygentheta",
        "api_key": "sk_33fe593b65d473a8e001e5887a8f0d9103431d442ca1dc89"
    },
    {
        "name": "vidiq",
        "api_key": "sk_8ee94716cfded63a38ce2eef7955960078f7476c53cf42ee"
    },
    {
        "name": "dexen62480@jio1.com",
        "api_key": "sk_e86c719c68a0074221bf4f35bd4be16dd5449dc19e300cad"
    },
    {
        "name": "yavoseh582@jio1.com",
        "api_key": "sk_fa67c2643449b54d9349cd1cea97b9083b5d85f4f5336f60"
    },
    {
        "name": "jsontham2005",
        "api_key": "sk_364b061acbdaa9de5abdd9425069426bf6f993b722c3e493"
    },
    {
        "name": "engineerai@theta.media",
        "api_key": "sk_c571a9e2062dd082d1372b6832588c7a2a33316e05c6767e"
    },
    {
        "name": "Louisa, Kelsey",
        "api_key": "sk_5304a4f30e8e7a4d7f5a0894583f11c83342241d5cb2f742"
    },
    {
        "name": "Non01",
        "api_key": "sk_9b51bbe1a3d9c2fa6da3e4595f0a9173f52ee906611ee302"
    },
    {
        "name": "jiminguyen",
        "api_key": "sk_c1828539c0189f3f61c9546207b17aab1a5e3eadaa7c9ce2"
    },
    {
       "name": "rayov80969@exitbit.com",
       "api_key": "sk_b73c0d43de28ba01234efec25f570e1b29e75db6c866a8a9" 
    },
    {
        "name": "facefev627@kimdyn.com",
        "api_key": "sk_d3746105565a2fa39ed2b4a86997134edb7a4c24374ddd9d"
    },
    {
        "name": "DarK Gartlink",
        "api_key": "sk_92ba76d44f3cdc659b81735dbac4a46744c500a0e022cad3"
    },
    {
        "name": "Sophia",
        "api_key": "sk_10ddde3fe7ffb1e87b2153199b8abee426d17511f15906c9"
    },
    {
        "name": "Alexandra",
        "api_key": "sk_00a58abed4706626de67061a2cbd6fac8355a74adcf4ee4f"
    }
]

PROXY_URL_1 = [
    "http://user49082:sBzct1Pt1m@45.194.28.84:49082"
]
PROXY_URL = [
    "http://ntbbaflx:nwvfil6623ww@198.23.239.134:6540",
    "http://ntbbaflx:nwvfil6623ww@45.38.107.97:6014",
    "http://ntbbaflx:nwvfil6623ww@107.172.163.27:6543",
    "http://ntbbaflx:nwvfil6623ww@64.137.96.74:6641",
    "http://ntbbaflx:nwvfil6623ww@45.43.186.39:6257",
    "http://ntbbaflx:nwvfil6623ww@154.203.43.247:5536",
    "http://ntbbaflx:nwvfil6623ww@84.247.60.125:6095",
    "http://ntbbaflx:nwvfil6623ww@216.10.27.159:6837",
    "http://ntbbaflx:nwvfil6623ww@136.0.207.84:6661",
    "http://ntbbaflx:nwvfil6623ww@142.147.128.93:6593"
]
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)


class CheckProxy:
    def check_proxy(proxy_url):
        try:
            cmd = [
                "curl", "-x", proxy_url, "--max-time", "5",
                "-s", "-o", "/dev/null", "-w", "%{http_code}",
                "https://httpbin.org/ip"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            status = result.stdout.strip()
            return status == "200", status
        except Exception as e:
            return False, str(e)
    def run():
        for proxy in PROXY_URL:
            ok, info = CheckProxy.check_proxy(proxy)
            status = "✅ OK" if ok else f"❌ FAIL: {info}"
            logging.info(f"{status} - {proxy}")


ERROR_PROXY= [
    "http://oxatkdbg:bgjri3i75l1j@64.64.118.149:6732",
    "http://oxatkdbg:bgjri3i75l1j@207.244.217.165:6712",
    "http://ycyczqee:fyr405a6f9at@104.239.105.125:6655",
    "http://ycyczqee:fyr405a6f9at@64.64.118.149:6732",
]