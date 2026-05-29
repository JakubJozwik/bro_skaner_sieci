import os
import time
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform

# Ręczny parser pliku .env.
# Dzięki temu unikamy konieczności instalowania zewnętrznych bibliotek (np. python-dotenv).
def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            # Pomijanie pustych linii i komentarzy
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Wczytanie konfiguracji z ukrytego pliku środowiskowego
load_env("/opt/bso_skaner/.env")

# Mapowanie zmiennych globalnych (z fallbackiem na wartości domyślne)
PATH_TO_SOCKET = os.getenv(
    "PATH_TO_SOCKET",
    "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock",
)
TARGET_IP = os.getenv("TARGET_IP", "192.168.1.0/24")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

GVM_USER = os.getenv("GVM_USER", "admin")
GVM_PASSWORD = os.getenv("GVM_PASSWORD", "admin")

# Walidator zmiennych środowiskowych. Przerywa dzialanie skryptu natychmiast, jezeli brakuje danych uwierzytelniajacych
def require_env():
    missing = [k for k in ["EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECEIVER"] if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"Brak wymaganych zmiennych środowiskowych: {', '.join(missing)}"
        )

# Pakuje odkodowany raport txt jako zalacznik binarnego strumienia i wysyla go przez uwierzytelniony kanal smtp do odbiorcy
def wyslij_email(txt_data, nazwa_pliku):
    print("[+] Wysyłka raportu e-mail...")
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = f"RAPORT BEZPIECZEŃSTWA: Sieć {TARGET_IP}"

    body = (
        "Witaj,\n\n"
        f"W załączeniu przesyłam raport podatności dla sieci {TARGET_IP} w formacie TXT.\n"
        "Raport wygenerowany automatycznie przez system skanowania N01.\n\n"
        "Pozdrawiam,\nSystem N01"
    )
    msg.attach(MIMEText(body, "plain"))
    
    # Przygotowanie zalacznika z raportem
    part = MIMEBase("application", "octet-stream")
    part.set_payload(txt_data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={nazwa_pliku}")
    msg.attach(part)
    
    # Nawiazywanie polaczenia z mailem i wysylka
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("[+] Raport wysłany poprawnie.")

# Mechanizm oczekujacy na gotowosc daemona gvm. Przy pierwszej instalacji zajmuje to troche czasu
def wait_for_gvm(gmp, timeout=1800):
    print("[+] Oczekiwanie na gotowość GVM ...")
    start = time.time()
    while True:
        try:
            gmp.get_version()
            print("[+] GVM jest gotowy.")
            return
        except Exception:
            if time.time() - start > timeout:
                raise TimeoutError("GVM nie wystartował w wymaganym czasie.")
            time.sleep(20)

# Pomocnicza funkcja parsujaca xml zwracane przez api gmp. Do wyszukiwania unikalnych identyfikatorw uuid po nazwie
def pick_by_name(xml, tag, name):
    for el in xml.findall(f".//{tag}"):
        n = el.find("name")
        if n is not None and n.text == name:
            return el.get("id")
    return None

# Main silnik skryptu. Realizuje pelny przebieg komunikacji z greenbone api: uwierzytelnienie, definicja celu, konfiguracja, start zadania, pooling, raport.
def prowadz_skanowanie():
    print("[+] Łączenie z silnikiem Greenbone...")
    # Nawiazqanie lokalnego polaczenia przez socket
    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()

    with Gmp(connection=connection, transform=transform) as gmp:
        wait_for_gvm(gmp)
        print("[+] Logowanie do API...")
        gmp.authenticate(GVM_USER, GVM_PASSWORD)

        # Port list, okreslenie listy portow do przeskanowania
        port_lists = gmp.get_port_lists()
        port_list_id = pick_by_name(port_lists, "port_list", "All IANA assigned TCP")
        if not port_list_id:
            # Fallback: pierwszy dostępny, jesli okresona lista nie istnieje
            pl = port_lists.find(".//port_list")
            if pl is None:
                raise RuntimeError("Brak list portów – GVM nie jest gotowy.")
            port_list_id = pl.get("id")

        # Target w bazie gvm
        print(f"[+] Tworzenie celu: {TARGET_IP}")
        response = gmp.create_target(
            name=f"Skan_{int(time.time())}",
            hosts=[TARGET_IP],
            port_list_id=port_list_id,
        )
        target_id = response.get("id")

        # Config Wybór profilu skanowania 
        configs = gmp.get_scan_configs()
        config_id = pick_by_name(configs, "config", "Full and fast")
        if not config_id:
            cfg = configs.find(".//config")
            if cfg is None:
                raise RuntimeError("Brak konfiguracji skanowania.")
            config_id = cfg.get("id")

        # Scanner Przypisanie domyślnego skanera (OpenVAS)
        scanners = gmp.get_scanners()
        scanner_id = pick_by_name(scanners, "scanner", "OpenVAS Default")
        if not scanner_id:
            sc = scanners.find(".//scanner")
            if sc is None:
                raise RuntimeError("Brak skanera.")
            scanner_id = sc.get("id")

        # Sklejenie celu, profilu i skanera w jedno Zadanie
        print("[+] Tworzenie zadania...")
        task = gmp.create_task(
            name="Zadanie BSO - Automatyczne",
            config_id=config_id,
            target_id=target_id,
            scanner_id=scanner_id,
        )
        task_id = task.get("id")
        
        # Uruchomienie fizycznego procesu skanowania
        print("[+] Start skanowania...")
        gmp.start_task(task_id)
        
        # Pętla nasłuchująca statusu wykonywania zadania (odświeżana co 30 sekund)
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            progress_elem = t.find(".//progress")
            progress = progress_elem.text if progress_elem is not None else "0"
            
            display_progress = "100" if status == "Done" else progress
            
            print(f"[*] Status: {status} ({display_progress}%)")
            if status in ["Done", "Stopped", "Finished"]:
                break
            time.sleep(30)
            
        # Pobranie ID wygenerowanego przez system raportu
        report_id = t.find(".//last_report/report").get("id")
        
        # Konfiguracja formatu eksportu na TXT
        formats = gmp.get_report_formats()
        txt_format_id = pick_by_name(formats, "report_format", "TXT")
        if not txt_format_id:
            raise RuntimeError(
                "Nie znaleziono formatu TXT. Poczekaj na feed report-formats."
            )

        print("[+] Generowanie raportu TXT...")
        report = gmp.get_report(
            report_id, report_format_id=txt_format_id, ignore_pagination=True
        )
        
        report_element = report.find(".//report")
        
        content = report_element.find("report_format").tail
        if not content:
            content = "".join(report_element.itertext())
            
        # Zdekodowanie natywnego formatu base64 zwracanego przez API do czystego tekstu
        txt_content = base64.b64decode(content)

        return txt_content

if __name__ == "__main__":
    print("=" * 50)
    print(" SYSTEM SKANOWANIA N01 (Raport TXT)")
    print("=" * 50)
    
    # Weryfikacja srodowiska przed wykonaniem operacji gvm
    require_env()

    try:
        # Zlecenie skanu i odebranie danych strumieniowych
        txt_data = prowadz_skanowanie()
        # Wysyl;ka odkodowwanych danych przez smtp
        wyslij_email(txt_data, "Raport_Sieci.txt")
    except Exception as e:
        print(f"[-] Błąd: {e}")

    print("=" * 50)
    print(" ZADANIE ZAKOŃCZONE")
    print("=" * 50)
