import pdfplumber
import json
import re

pdf_path = r"Z:\Rick Garner\Documentation\MoveIT\Environment Diagrams\BSOC MOVEit Environment V1.08 09.07.2023.pdf"

with pdfplumber.open(pdf_path) as pdf:
    full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

# Extract IP addresses
ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
ip_addresses = re.findall(ip_pattern, full_text)

# Extract server names (looking for patterns like BSOAUTALB001, etc.)
server_pattern = r'\b([A-Z]+[A-Z0-9]{2,})\b'
server_names = re.findall(server_pattern, full_text)

# Extract domain names
domain_pattern = r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})\b'
domains = re.findall(domain_pattern, full_text)

# Extract URLs
url_pattern = r'\b(https?://[^\s<>"{}|\\^`\[\]]+)\b'
urls = re.findall(url_pattern, full_text)

# Extract email addresses
email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
emails = re.findall(email_pattern, full_text)

# Extract port numbers
port_pattern = r'\b(port|Port)\s*[:=]?\s*(\d{1,5})\b'
ports = re.findall(port_pattern, full_text, re.IGNORECASE)

# Extract database/server references
db_pattern = r'\b(sql|SQL|database|Database|server|Server|instance|Instance)\b'
db_refs = re.findall(db_pattern, full_text, re.IGNORECASE)

print("=" * 80)
print("MOVEit Environment Information Extracted from PDF")
print("=" * 80)
print()

print("IP ADDRESSES:")
print("-" * 40)
unique_ips = list(set(ip_addresses))
for ip in unique_ips:
    print(f"  {ip}")
print()

print("SERVER NAMES:")
print("-" * 40)
unique_servers = list(set(server_names))
for server in unique_servers:
    print(f"  {server}")
print()

print("DOMAIN NAMES:")
print("-" * 40)
unique_domains = list(set(domains))
for domain in unique_domains:
    print(f"  {domain}")
print()

print("URLs:")
print("-" * 40)
for url in urls:
    print(f"  {url}")
print()

print("EMAIL ADDRESSES:")
print("-" * 40)
for email in emails:
    print(f"  {email}")
print()

print("PORTS:")
print("-" * 40)
unique_ports = list(set([p[1] for p in ports]))
for port in unique_ports:
    print(f"  {port}")
print()

print("DATABASE/SERVER REFERENCES:")
print("-" * 40)
print(f"  Count: {len(db_refs)}")
print()

print("FULL TEXT PREVIEW:")
print("-" * 40)
print(full_text[:2000] if len(full_text) > 2000 else full_text)
print()

# Save structured data
output_data = {
    "ip_addresses": unique_ips,
    "server_names": unique_servers,
    "domain_names": unique_domains,
    "urls": urls,
    "email_addresses": emails,
    "ports": unique_ports,
    "database_server_references": len(db_refs),
    "full_text": full_text
}

output_path = "storage/moveit-pdf-extraction-2026-09-23.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2)

print(f"Structured data saved to: {output_path}")
