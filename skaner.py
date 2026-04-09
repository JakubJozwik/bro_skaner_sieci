import time
import smtplib
import os
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
PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"

# DO PREZENTACJI UŻYJ POJEDYNCZEGO IP (np. bramy/routera), INACZEJ SKAN ZAJMIE 10 GODZIN!
TARGET_IP = "192.168.1.1" 

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def wyslij_email(pdf_data, nazwa_pliku):
    print("[+] Przygotowuję wysyłkę wiadomości e-mail...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"RAPORT BEZPIECZEŃSTWA: Urządzenie/Sieć {TARGET_IP}"
    
    body = (
        f"Witaj,\n\n"
        f"Zakończono automatyczne badanie bezpieczeństwa sieci dla celu: {TARGET_IP}.\n"
        f"W załączeniu znajduje się pełny raport w formacie PDF wygenerowany przez Greenbone Vulnerability Scanner.\n\n"
        f"Z poważaniem,\nSystem N01"
    )
    msg.attach(MIMEText(body, 'plain'))
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_data)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename={nazwa_pliku}")
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] Raport e-mail został wysłany pomyślnie!")
    except Exception as e:
        print(f"[-] Błąd podczas wysyłania e-maila: {e}")

def prowadz_skanowanie():
    print("[+] Nawiązywanie połączenia z API Greenbone...")
    if not os.path.exists(PATH_TO_SOCKET):
        raise Exception(f"Gniazdo API {PATH_TO_SOCKET} nie istnieje! Docker prawdopodobnie jeszcze go nie utworzył.")

    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()
    
    with Gmp(connection=connection, transform=transform) as gmp:
        print("[+] Autoryzacja...")
        gmp.authenticate("admin", "admin")
        
        # Oczekiwanie na gotowość skanera (Zabezpieczenie przed błędem wczesnego uruchomienia)
        configs = gmp.get_scan_configs()
        config_id = None
        for c in configs.findall('.//config'):
            if c.find('name').text == 'Full and fast':
                config_id = c.get('id')
                break
                
        if not config_id:
             raise Exception("Skaner pobiera bazy podatności (NVT/SCAP). Konfiguracje nie są jeszcze gotowe. Odczekaj kilkadziesiąt minut.")

        # Pobieranie Listy Portów
        port_lists = gmp.get_port_lists()
        port_list_id = None
        for pl in port_lists.findall('.//port_list'):
            if "All IANA assigned TCP" in pl.find('name').text:
                port_list_id = pl.get('id')
                break
        # Jeśli nie ma "All IANA", bierzemy pierwszą z brzegu
        if not port_list_id:
            port_list_id = port_lists.find('.//port_list').get('id') 

        print(f"[+] Konfigurowanie celu skanowania: {TARGET_IP}")
        target_res = gmp.create_target(name=f"Automatyczny_Cel_{int(time.time())}", hosts=[TARGET_IP], port_list_id=port_list_id)
        target_id = target_res.get('id')
        
        # Pobieranie ID Skanera "OpenVAS Default"
        scanners = gmp.get_scanners()
        scanner_id = None
        for s in scanners.findall('.//scanner'):
            if s.find('name').text == 'OpenVAS Default':
                scanner_id = s.get('id')
                break

        print("[+] Generowanie zlecenia skanowania (Task)...")
        task = gmp.create_task(name="Zadanie N01", config_id=config_id, target_id=target_id, scanner_id=scanner_id)
        task_id = task.get('id')
        
        print("[+] Startowanie Skanera. Proszę czekać, to może potrwać do kilkunastu minut...")
        gmp.start_task(task_id)
        
        # Monitorowanie postępu (Co 30 sekund)
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            
            # Zapobieganie crashom, gdy progress jeszcze nie posiada wartości
            progress_elem = t.find(".//progress")
            progress = progress_elem.text if progress_elem is not None else "0"
            if progress == "-1": progress = "0"
            
            print(f"[*] Postęp skanowania: {status} ({progress}%)")
            
            if status in ["Done", "Stopped", "Finished"]:
                break
            time.sleep(30)
            
        print("[+] Pobieranie wygenerowanego raportu PDF...")
        report_id = t.find(".//last_report/report").get("id")
        
        formats = gmp.get_report_formats()
        pdf_format_id = None
        for f in formats.findall('.//report_format'):
            if f.find('name').text == 'PDF':
                pdf_format_id = f.get('id')
                break
                
        report = gmp.get_report(report_id, report_format_id=pdf_format_id, ignore_pagination=True)
        import base64
        pdf_content = base64.b64decode(report.find(".//report").text)
        
        return pdf_content

if __name__ == "__main__":
    # Blokada zabezpieczająca
    if os.geteuid() != 0:
        print("[-] BŁĄD KRYTYCZNY: Uruchom skrypt jako root (sudo)! W przeciwnym razie nie masz dostępu do gniazda Dockera.")
        exit(1)

    print("="*50)
    print(" ZAAWANSOWANY SKANER SIECI (N01) - START ")
    print("="*50)
    
    try:
        pdf_data = prowadz_skanowanie()
        wyslij_email(pdf_data, "Greenbone_Raport_Sieciowy.pdf")
    except Exception as e:
        print("\n[-] PRZERWANO Z POWODU BŁĘDU:")
        print(f"    {e}")
        print("\n[!] Jeżeli API zgłasza błąd z konfiguracjami lub skanerem,")
        print("        oznacza to, że kontenery GVM wciąż pobierają bazy wirusów i luk.")
        print("        Sprawdź ich logi poleceniem: 'sudo docker compose -p greenbone-community-edition logs -f notus-data'")
        print("        Z reguły pierwsze uruchomienie zajmuje do 2 godzin!")
        
    print("="*50)
    print(" SYSTEM N01 ZAKOŃCZYŁ DZIAŁANIE ")
    print("="*50)
