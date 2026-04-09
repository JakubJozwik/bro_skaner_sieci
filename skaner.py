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
# Ścieżka do gniazda komunikacyjnego kontenera (standard w Dockerze dla GVM)
PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"
TARGET_IP = "192.168.1.0/24" # Adres Twojej sieci

# Konfiguracja poczty wychodzącej (najlepiej użyć konta Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "basketkuba.05@gmail.com"
# UWAGA: Do Gmaila nie wpisujesz zwykłego hasła, tylko 16-znakowe "Hasło Aplikacji" 
# (do wygenerowania w ustawieniach konta Google w zakładce Bezpieczeństwo)
EMAIL_PASSWORD ="bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def wyslij_email(pdf_data, nazwa_pliku):
    print("[+] Przygotowuję wysyłkę prawdziwego raportu PDF...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"RAPORT BEZPIECZEŃSTWA: Sieć {TARGET_IP}"
    
    body = (
        f"Witaj,\n\n"
        f"W załączeniu przesyłam pełny, automatycznie wygenerowany raport podatności "
        f"dla sieci {TARGET_IP}. Skan został wykonany przez silnik Greenbone.\n\n"
        f"Pozdrawiam,\nSystem N01 (BSO)"
    )
    msg.attach(MIMEText(body, 'plain'))
    
    # Dołączanie surowych danych PDF
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_data)
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
        # 1. Logowanie (używamy domyślnych danych z oficjalnego kontenera)
        print("[+] Logowanie do API (admin/admin)...")
        gmp.authenticate("admin", "admin")
        
        # 2. Pobranie ID domyślnej listy portów (wymagane w nowych wersjach GVM)
        print("[+] Pobieranie domyślnej listy portów do skanowania...")
        port_lists_response = gmp.get_port_lists()
        # Wyciągamy ID pierwszej dostępnej listy (zazwyczaj "All IANA assigned TCP")
        port_list_id = port_lists_response.find('.//port_list').get('id')

        # 3. Tworzenie celu (Target) w bazie skanera z wymaganymi portami
        print(f"[+] Konfiguracja celu skanowania: {TARGET_IP}")
        response = gmp.create_target(
            name=f"Skan_{int(time.time())}", 
            hosts=[TARGET_IP], 
            port_list_id=port_list_id
        )
        target_id = response.get('id')
        
        # 3. Pobranie ID domyślnej konfiguracji skanu (tzw. Full and Fast)
        configs = gmp.get_scan_configs()
        # Wybieramy pierwszy podstawowy profil
        config_id = configs[0].get('id') 
        
        # 4. Tworzenie i uruchomienie zadania
        print("[+] Tworzenie zadania skanowania...")
        # scanner_id to domyślny skaner OpenVAS w systemie Greenbone
        task = gmp.create_task(
            name="Zadanie BSO - Automatyczne", 
            config_id=config_id, 
            target_id=target_id, 
            scanner_id="08b69003-5fc2-4037-a479-93b440211c73"
        )
        task_id = task.get('id')
        
        print("[+] Uruchamianie skanera. To potrwa (od 15 minut do paru godzin zależnie od sieci)...")
        gmp.start_task(task_id)
        
        # 5. Monitorowanie postępu (Czekamy, aż skaner skończy pracę)
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            
            # Zapobiegamy błędowi, gdy progress jeszcze nie istnieje (wczesna faza 'Requested')
            progress_elem = t.find(".//progress")
            progress = progress_elem.text if progress_elem is not None else "0"
            
            print(f"[*] Status: {status} ({progress}%)")
            
            if status in ["Done", "Stopped", "Finished"]:
                break
                
            time.sleep(30) # Odpytuj silnik co 30 sekund
            
        # 6. Pobranie raportu
        report_id = t.find(".//last_report/report").get("id")
        
        print("[+] Wyszukiwanie formatu PDF w bazie serwera...")
        formats_response = gmp.get_report_formats()
        pdf_format_id = None
        
        # Przeszukujemy listę wszystkich dostępnych formatów (XML, CSV, TXT, PDF...)
        for f in formats_response.findall('.//report_format'):
            if f.find('name').text == 'PDF':
                pdf_format_id = f.get('id')
                break
                
        if not pdf_format_id:
            raise Exception("Nie znaleziono formatu PDF! Kontener 'report-formats' wciąż wgrywa dane.")
        
        print("[+] Generowanie końcowego dokumentu PDF...")
        report = gmp.get_report(report_id, report_format_id=pdf_format_id, ignore_pagination=True)
        
        # Wyciąganie surowych danych PDF (są zakodowane w base64 wewnątrz odpowiedzi XML)
        import base64
        pdf_content = base64.b64decode(report.find(".//report").text)
        
        return pdf_content

if __name__ == "__main__":
    print("="*50)
    print(" PEŁNOPRAWNY SYSTEM SKANOWANIA SIECI (API GMP)")
    print("="*50)
    
    try:
        pdf_data = prowadz_skanowanie()
        wyslij_email(pdf_data, "Prawdziwy_Raport_Sieci.pdf")
    except Exception as e:
        print(f"[-] Otrzymano błąd z silnika: {e}")
        print("    Wskazówka: Jeśli to błąd 'Scanner not available' lub podobny,")
        print("    oznacza to, że kontenery pobierają bazę NVT w tle. Daj im około godziny.")
        
    print("="*50)
    print(" ZADANIE ZAKOŃCZONE")
    print("="*50)
