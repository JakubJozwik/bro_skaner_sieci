import time
import smtplib
import socket
import os
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- KONFIGURACJA ---
# Ścieżka dynamiczna (zależna od nazwy projektu w Install.sh)
PATH_TO_SOCKET = "/var/lib/docker/volumes/bso-n01_gvmd_socket_vol/_data/gvmd.sock"
EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def pobierz_ip():
    """Wykrywa lokalny adres IP maszyny"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def wyslij_email(tresc, cel):
    """Wysyła wyniki skanowania na e-mail"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"RAPORT BEZPIECZEŃSTWA N01 - {cel}"
    msg.attach(MIMEText(tresc, 'plain'))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] Mail wysłany pomyślnie!")
    except Exception as e:
        print(f"[-] Błąd wysyłki e-mail: {e}")

def prowadz_skanowanie():
    """Główna logika komunikacji z API Greenbone"""
    from gvm.connections import UnixSocketConnection
    from gvm.protocols.gmp import Gmp
    from gvm.transforms import EtreeCheckCommandTransform

    cel = pobierz_ip()
    print(f"[!] Rozpoczynam skanowanie celu: {cel}")
    
    if not os.path.exists(PATH_TO_SOCKET):
        raise Exception("Gniazdo API (Socket) nie zostało jeszcze utworzone. Poczekaj kilka minut.")

    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    with Gmp(connection=connection, transform=EtreeCheckCommandTransform()) as gmp:
        gmp.authenticate("admin", "admin")
        
        # Pobieranie niezbędnych ID z API
        try:
            cfg_id = gmp.get_scan_configs()[0].get('id')
            ports_id = gmp.get_port_lists()[0].get('id')
        except IndexError:
            raise Exception("Bazy danych skanera nie są jeszcze gotowe (NVT Sync). Odczekaj 15 minut.")

        # 1. Tworzenie celu (Target)
        tgt = gmp.create_target(
            name=f"Skan_{int(time.time())}", 
            hosts=[cel], 
            port_list_id=ports_id, 
            alive_test="Consider Alive"
        )
        tgt_id = tgt.get('id')
        
        # 2. Tworzenie i start zadania (Task)
        task = gmp.create_task(
            name=f"Zadanie_{cel}", 
            config_id=cfg_id, 
            target_id=tgt_id, 
            scanner_id="08b69003-5fc2-4037-a479-93b440211c73"
        )
        task_id = task.get('id')
        gmp.start_task(task_id)
        
        # 3. Monitorowanie postępu
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            prog = t.find(".//progress").text if t.find(".//progress") is not None else "0"
            print(f"[*] Status: {status} ({prog}%)")
            if status in ["Done", "Stopped", "Finished"]:
                break
            time.sleep(20)
            
        print("[+] Pobieranie wyników z bazy danych...")
        time.sleep(10) # Czas na sfinalizowanie zapisu
        
        # 4. Pobieranie raportu (Wyszukiwanie po ID zadania)
        reports = gmp.get_reports()
        rid = None
        for r in reports.findall(".//report"):
            if r.find("task").get("id") == task_id:
                rid = r.get("id")
                break
        
        report_data = gmp.get_report(rid, details=True)
        
        # Budowanie treści raportu tekstowego
        wyniki = f"RAPORT SKANOWANIA SIECI LOKALNEJ (N01)\n"
        wyniki += f"CEL: {cel}\n"
        wyniki += "="*40 + "\n\n"
        
        found = False
        for rs in report_data.findall(".//results/result"):
            found = True
            severity = rs.find('severity').text
            name = rs.find('name').text
            port = rs.find('port').text
            wyniki += f"[{severity}] {name}\nPORT: {port}\n"
            wyniki += "-"*20 + "\n"
        
        if not found:
            wyniki += "Nie znaleziono krytycznych podatności. System jest bezpieczny."
        
        return wyniki, cel

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("BŁĄD: Uruchom skrypt jako root (sudo python3 ...)")
        exit(1)
        
    try:
        r, c = prowadz_skanowanie()
        wyslij_email(r, c)
    except Exception as e:
        print(f"[-] BŁĄD KRYTYCZNY: {e}")
