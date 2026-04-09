import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform

# ==========================================
# KONFIGURACJA SKANERA I RAPORTOWANIA
# ==========================================
# Ścieżka do gniazda komunikacyjnego kontenera
PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock" 
TARGET_IP = "192.168.1.0/24" # Adres Twojej sieci

EMAIL_SENDER = "twoj_mail@gmail.com"
EMAIL_PASSWORD = "twoje_16_znakowe_haslo_aplikacji"
EMAIL_RECEIVER = "twoj_mail@gmail.com"

def wyslij_email(raport_data, nazwa_pliku):
    print("[+] Przygotowuję wysyłkę prawdziwego raportu...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"RAPORT BEZPIECZEŃSTWA: Sieć {TARGET_IP}"
    
    body = (
        f"Witaj,\n\n"
        f"W załączeniu przesyłam pełny, automatycznie wygenerowany raport podatności "
        f"dla sieci {TARGET_IP} w formacie TXT (obejście problemu PDF na ARM).\n\n"
        f"Pozdrawiam,\nSystem N01 (BSO)"
    )
    msg.attach(MIMEText(body, 'plain'))
    
    # Dołączanie surowych danych
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(raport_data)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename={nazwa_pliku}")
    msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] Raport wysłany pomyślnie na Twój e-mail!")
    except Exception as e:
        print(f"[-] Błąd SMTP (Sprawdź hasło aplikacji): {e}")

def prowadz_skanowanie():
    print("[+] Łączenie z silnikiem Greenbone (Unix Socket)...")
    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()
    
    with Gmp(connection=connection, transform=transform) as gmp:
        print("[+] Logowanie do API (admin/admin)...")
        gmp.authenticate("admin", "admin")
        
        print("[+] Pobieranie domyślnej listy portów do skanowania...")
        port_lists_response = gmp.get_port_lists()
        port_list_id = port_lists_response.find('.//port_list').get('id')

        print(f"[+] Konfiguracja celu skanowania: {TARGET_IP}")
        response = gmp.create_target(
            name=f"Skan_{int(time.time())}", 
            hosts=[TARGET_IP], 
            port_list_id=port_list_id
        )
        target_id = response.get('id')
        
        configs = gmp.get_scan_configs()
        config_id = configs[0].get('id') 
        
        print("[+] Tworzenie zadania skanowania...")
        task = gmp.create_task(
            name="Zadanie BSO - Automatyczne", 
            config_id=config_id, 
            target_id=target_id, 
            scanner_id="08b69003-5fc2-4037-a479-93b440211c73"
        )
        task_id = task.get('id')
        
        print("[+] Uruchamianie skanera. To potrwa (od 15 minut do paru godzin zależnie od sieci)...")
        gmp.start_task(task_id)
        
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            
            progress_elem = t.find(".//progress")
            progress = progress_elem.text if progress_elem is not None else "0"
            
            print(f"[*] Status: {status} ({progress}%)")
            
            if status in ["Done", "Stopped", "Finished"]:
                break
                
            time.sleep(30)
            
        report_id = t.find(".//last_report/report").get("id")
        
        print("[+] Wyszukiwanie formatu TXT w bazie serwera (obejscie problemu architektury ARM)...")
        formats_response = gmp.get_report_formats()
        txt_format_id = None
        
        for f in formats_response.findall('.//report_format'):
            if f.find('name').text == 'TXT':
                txt_format_id = f.get('id')
                break
                
        if not txt_format_id:
            raise Exception("Nie znaleziono formatu TXT!")
        
        print("[+] Pobieranie surowego raportu tekstowego...")
        report = gmp.get_report(report_id, report_format_id=txt_format_id, ignore_pagination=True)
        
        import base64
        txt_content = base64.b64decode(report.find(".//report").text)
        
        return txt_content

if __name__ == "__main__":
    print("="*50)
    print(" PEŁNOPRAWNY SYSTEM SKANOWANIA SIECI (API GMP)")
    print("="*50)
    
    try:
        txt_data = prowadz_skanowanie()
        wyslij_email(txt_data, "Prawdziwy_Raport_Sieci.txt")
    except Exception as e:
        print(f"[-] Otrzymano błąd z silnika: {e}")
        
    print("="*50)
    print(" ZADANIE ZAKOŃCZONE")
    print("="*50)
