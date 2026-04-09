import time, smtplib, socket, os, xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

PATH_TO_SOCKET = "/var/lib/docker/volumes/greenbone-community-edition_gvmd_socket_vol/_data/gvmd.sock"
EMAIL_SENDER = "basketkuba.05@gmail.com"
EMAIL_PASSWORD = "bhck irya mxdj xdec" 
EMAIL_RECEIVER = "basketkuba.05@gmail.com"

def pobierz_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def wyslij_email(tresc, cel):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"RAPORT N01 - CEL: {cel}"
    msg.attach(MIMEText(tresc, 'plain'))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("[+] MAIL WYSLANY!")
    except Exception as e: print(f"[-] Blad SMTP: {e}")

def prowadz_skanowanie():
    from gvm.connections import UnixSocketConnection
    from gvm.protocols.gmp import Gmp
    from gvm.transforms import EtreeCheckCommandTransform

    cel = pobierz_ip()
    print(f"[!] Start: {cel}")
    with Gmp(connection=UnixSocketConnection(path=PATH_TO_SOCKET), transform=EtreeCheckCommandTransform()) as gmp:
        gmp.authenticate("admin", "admin")
        
        cfg_id = gmp.get_scan_configs()[0].get('id')
        tgt = gmp.create_target(name=f"S_{int(time.time())}", hosts=[cel], port_list_id=gmp.get_port_lists()[0].get('id'), alive_test="Consider Alive")
        tgt_id = tgt.get('id')
        
        task = gmp.create_task(name="Zadanie_BSO", config_id=cfg_id, target_id=tgt_id, scanner_id="08b69003-5fc2-4037-a479-93b440211c73")
        tid = task.get('id')
        gmp.start_task(tid)
        
        while True:
            t = gmp.get_task(tid)
            status = t.find(".//status").text
            print(f"[*] Status: {status}")
            if status in ["Done", "Stopped", "Finished"]: break
            time.sleep(20)
            
        print("[+] Pobieranie danych...")
        time.sleep(15)
        
        # Pobieranie raportu (metoda kompatybilna ze wszystkimi wersjami)
        r_list = gmp.get_reports()
        rid = None
        for r in r_list.findall(".//report"):
            if r.find("task").get("id") == tid:
                rid = r.get("id")
                break
        
        res = gmp.get_report(rid, details=True)
        wyniki = f"RAPORT DLA: {cel}\n" + "="*30 + "\n"
        found = False
        for rs in res.findall(".//results/result"):
            found = True
            wyniki += f"[{rs.find('severity').text}] {rs.find('name').text} (Port: {rs.find('port').text})\n"
        
        if not found: wyniki += "Brak podatnosci."
        return wyniki, cel

if __name__ == "__main__":
    try:
        r, c = prowadz_skanowanie()
        wyslij_email(r, c)
    except Exception as e: print(f"[-] Blad: {e}")
