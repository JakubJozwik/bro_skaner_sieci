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
TARGET_IP = "8.8.8.8" 

EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def wyslij_email(tresc):
    print(f"[+] Wysyłanie wyników na adres: {EMAIL_RECEIVER}")
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
        print("[+] MAIL WYSLANY POMYŚLNIE!")
    except Exception as e: print(f"[-] Błąd SMTP: {e}")

def prowadz_skanowanie():
    from gvm.connections import UnixSocketConnection
    from gvm.protocols.gmp import Gmp
    from gvm.transforms import EtreeCheckCommandTransform

    print(f"[!] Start procedury dla: {TARGET_IP}")
    connection = UnixSocketConnection(path=PATH_TO_SOCKET)
    transform = EtreeCheckCommandTransform()
    
    with Gmp(connection=connection, transform=transform) as gmp:
        gmp.authenticate("admin", "admin")
        
        # Pobieranie konfiguracji
        configs = gmp.get_scan_configs()
        config_id = configs[0].get('id')
        port_list_id = gmp.get_port_lists()[0].get('id')
        
        # Cel i Zadanie
        target = gmp.create_target(name=f"Final_{int(time.time())}", hosts=[TARGET_IP], port_list_id=port_list_id, alive_test="Consider Alive")
        target_id = target.get('id')
        
        task = gmp.create_task(name="Zadanie Koncowe", config_id=config_id, target_id=target_id, scanner_id="08b69003-5fc2-4037-a479-93b440211c73")
        task_id = task.get('id')
        gmp.start_task(task_id)
        
        print("[+] Skanowanie w toku... Czekaj na wyniki.")
        while True:
            t = gmp.get_task(task_id)
            status = t.find(".//status").text
            prog = t.find(".//progress").text if t.find(".//progress") is not None else "0"
            print(f"[*] Status: {status} ({prog}%)")
            # Jeśli status to Done, Stopped lub Finished - wychodzimy
            if status in ["Done", "Stopped", "Finished"]: break
            time.sleep(15)
            
        print("[+] Pobieranie raportu z bazy danych...")
        time.sleep(5)
        
        # POBIERANIE RAPORTU (Metoda odporna na błędy)
        # Szukamy raportu powiązanego z naszym task_id
        reports = gmp.get_reports(filter=f"task_id={task_id}")
        report_elem = reports.find(".//report")
        
        if report_elem is None:
            raise Exception("Nie znaleziono raportu dla tego zadania w bazie danych.")
            
        report_id = report_elem.get("id")
        
        # Pobieramy pełne detale raportu w formacie XML
        response = gmp.get_report(report_id, details=True)
        
        wyniki = f"RAPORT SKANOWANIA N01\nCEL: {TARGET_IP}\nSTATUS: {status}\n"
        wyniki += "="*40 + "\n\n"
        
        found = False
        for result in response.findall(".//results/result"):
            found = True
            name = result.find("name").text
            port = result.find("port").text
            severity = result.find("severity").text
            wyniki += f"[{severity}] {name}\nPORT: {port}\n"
            wyniki += "-"*20 + "\n"
            
        if not found:
            wyniki += "Skanowanie nie wykazało podatności (prawdopodobnie przez zatrzymanie zadania)."
            
        return wyniki

if __name__ == "__main__":
    try:
        raport = prowadz_skanowanie()
        wyslij_email(raport)
    except Exception as e: print(f"[-] BŁĄD KRYTYCZNY: {e}")
