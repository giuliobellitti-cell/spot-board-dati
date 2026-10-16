import re, urllib.request
UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25).read().decode("utf-8","replace")
t=get("https://www.meteosystem.com/stazione/marinadorica/dati.php")
txt=re.sub(r"<[^>]+>"," ",t); txt=re.sub(r"\s+"," ",txt)
i=txt.find("aggiornati"); print("METEOSYSTEM:", txt[max(0,i-40):i+120])
j=txt.lower().find("vento"); print("METEOSYSTEM vento:", txt[j:j+200])
for sid in ["IPESAR14","IFANO17"]:
    w=get("https://www.wunderground.com/dashboard/pws/"+sid)
    for key in ["obsTimeLocal","windSpeed","winddir","windGust","apiKey"]:
        m=re.search(r'.{0,60}'+key+r'.{0,80}',w)
        print("WU",sid,key,":",m.group(0).replace("\n"," ") if m else "—")
e=get("https://www.ecowitt.net/home/share?authorize=UB1MKB&device_id=MDJsaVpjZ2JXZGErMzdtcjJqR2RsUT09")
print("ECOWITT script/api hints:", sorted(set(re.findall(r'["\'](/[a-zA-Z_/]*(?:index|api|share|data)[a-zA-Z_/]*)["\']',e)))[:20])
