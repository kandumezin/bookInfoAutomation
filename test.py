import xml.etree.ElementTree as ET

with open("res.txt", mode="r", encoding="UTF-8") as f:
    root = ET.fromstring(f.read())
    xml = root.find(".//item")

for i in xml:
    print(i.tag, i.text)