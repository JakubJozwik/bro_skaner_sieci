import time
import smtplib
import socket
import os
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==========================================
# KONFIGURACJA
# ==========================================
PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"

def pobierz_moje_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

TARGET_IP = pobierz_moje_ip()
EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def wyslij_email(tresc):
    print(f"[+] Wysyłanie raportu na adres: {EMAIL_RECEIVER}")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"FINALNY RAPORT SKANOWANIA N01 - {TARGET_IP}"
    msg.attach(MIMEText(tresc, 'plain'))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] RAPORT WYSLANY NA E-MAIL!")
    except Exception as e: print(f"[-] Błąd SMTP: {e}")

def prowadz_skanowanie():
    from gvm.connections import UnixSocketConnection
    from gvm.protocols.gmp import Gmp
    from gvm.transforms import EtreeCheckCommandTransform

    print(f"[!] Start procedury dla: {TARGET_IP}")
    if not os.path.exists(PATH_TO_SOCKET):
        raise Exception("Gniazdo API jeszcze nie gotowe.")

    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()
    
    with Gmp(connection=connection, transform=transform) as gmp:
        gmp.authenticate("admin", "admin")
        
        configs = gmp.get_scan_configs()
        config_id = configs[0].get('id')
        port_list_id = gmp.get_port_lists()[0].get('id')
        
        target = gmp.create_target(name=f"Skan_{int(time.time())}", hosts=[TARGET_IP], port_list_id=port_list_id, alive_test="Consider Alive")
        target_id = target.get('id')
        
        task = gmp.create_task(name=f"Zadanie_{TARGET_IP}", config_id=config_id, target_id=target_id, scanner_id="08b69003-5fc2-4037-a479-93b440211c73")
        task_id = task.get('id')
        gmp.start_task(task_id)
        
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            prog = t.find(".//progress").text if t.find(".//progress") is not None else "0"
            print(f"[*] Status: {status} ({prog}%)")
            if status in ["Done", "Stopped", "Finished"]: break
            time.sleep(20)
            
        print("[+] Pobieranie danych z bazy (bez filtrów)...")
        time.sleep(10)
        
        # POBIERANIE RAPORTU - NOWA METODA DLA GMPv226
        all_reports = gmp.get_reports()
        report_id = None
        
        for r in all_reports.findall(".//report"):
            task_node = r.find("task")
            if task_node is not None and task_node.get("id") == task_id:
                report_id = r.get("id")
                break
        
        if not report_id:
            raise Exception("Nie znaleziono raportu dla tego zadania.")
        
        response = gmp.get_report(report_id, details=True)
        
        wyniki = f"RAPORT SKANOWANIA SIECI N01\nCEL: {TARGET_IP}\nSTATUS: {status}\n"
        wyniki += "="*40 + "\n\n"
        
        found = False
        for result in response.findall(".//results/result"):
            found = True
            name_node = result.find("name")
            port_node = result.find("port")
            sev_node = result.find("severity")
            
            name = name_node.text if name_node is not None else "Unknown"
            port = port_node.text if port_node is not None else "Unknown"
            severity = sev_node.text if sev_node is not None else "Info"
            
            wyniki += f"[{severity}] {name}\nPORT: {port}\n"
            wyniki += "-"*20 + "\n"
            
        if not found:
            wyniki += "Skanowanie nie wykazalo krytycznych podatnosci."
            
        return wyniki

if __name__ == "__main__":
    try:
        raport = prowadz_skanowanie()
        wyslij_email(raport)
    except Exception as e: print(f"[-] BŁĄD KRYTYCZNY: {e}")
