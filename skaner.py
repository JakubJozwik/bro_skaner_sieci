import time
import smtplib
import socket
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform

# ==========================================
# KONFIGURACJA SYSTEMU I RAPORTOWANIA
# ==========================================
PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"

def pobierz_lokalne_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

TARGET_IP = pobierz_lokalne_ip()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def wyslij_email(raport_text):
    print(f"[+] Wysyłanie raportu tekstowego na adres: {EMAIL_RECEIVER}")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"Raport Bezpieczeństwa N01 - Cel: {TARGET_IP}"
    
    body = f"Dzień dobry,\n\nAutomatyczny skan podatności dla adresu {TARGET_IP} został zakończony.\nRaport w formie pliku tekstowego znajduje się w załączniku.\n\nPozdrawiamy,\nSystem N01 (BSO)"
    msg.attach(MIMEText(body, 'plain'))
    
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(raport_text)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="Raport_Skanowania.txt"')
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] E-mail z raportem TXT wysłany!")
    except Exception as e:
        print(f"[-] Błąd SMTP: {e}")

def prowadz_skanowanie():
    print(f"[!] Rozpoczynam procedurę dla celu: {TARGET_IP}")
    if not os.path.exists(PATH_TO_SOCKET):
        raise Exception("Brak gniazda API. Silnik Greenbone jeszcze się uruchamia.")

    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()
    
    with Gmp(connection=connection, transform=transform) as gmp:
        gmp.authenticate("admin", "admin")
        
        configs = gmp.get_scan_configs()
        config_id = None
        for c in configs.findall('.//config'):
            if "Full and fast" in c.find('name').text:
                config_id = c.get('id')
                break
        
        if not config_id:
            raise Exception("Bazy NVT wciąż się synchronizują. Spróbuj za chwilę.")

        port_list_id = gmp.get_port_lists()[0].get('id')

        print("[+] Tworzenie celu skanowania...")
        target_res = gmp.create_target(
            name=f"Skan_{int(time.time())}", 
            hosts=[TARGET_IP], 
            port_list_id=port_list_id,
            alive_test="Consider Alive"
        )
        target_id = target_res.get('id')
        
        scanner_id = "08b69003-5fc2-4037-a479-93b440211c73"

        print("[+] Startowanie zadania...")
        task = gmp.create_task(name=f"Zadanie_{TARGET_IP}", config_id=config_id, target_id=target_id, scanner_id=scanner_id)
        task_id = task.get('id')
        gmp.start_task(task_id)
        
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            prog_elem = t.find(".//progress")
            prog = prog_elem.text if prog_elem is not None else "0"
            print(f"[*] Postęp: {status} ({prog}%)")
            if status in ["Done", "Stopped", "Finished"]:
                break
            time.sleep(30)
            
        print("[+] Skanowanie zakończone. Czekam 30s na sfinalizowanie bazy raportów...")
        time.sleep(30)

        print("[+] Pobieranie raportu w formacie TXT...")
        report_id = t.find(".//last_report/report").get("id")
        
        txt_format_id = None
        for f in gmp.get_report_formats().findall('.//report_format'):
            # Szukamy formatu TXT lub Text
            if f.find('name').text in ['TXT', 'Text']:
                txt_format_id = f.get('id')
                break
                
        if not txt_format_id:
            # Jeśli nie ma TXT, weźmiemy cokolwiek co nie jest PDF (np. Anonymous XML)
            txt_format_id = gmp.get_report_formats()[0].get('id')

        report = gmp.get_report(report_id, report_format_id=txt_format_id, ignore_pagination=True)
        raw_report = report.find(".//report").text
        
        if raw_report is None:
            raise Exception("Serwer nadal nie udostępnił treści raportu.")

        return base64.b64decode(raw_report)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Uruchom jako root (sudo)!")
        exit(1)
    try:
        data = prowadz_skanowanie()
        wyslij_email(data)
    except Exception as e:
        print(f"[-] BŁĄD: {e}")
