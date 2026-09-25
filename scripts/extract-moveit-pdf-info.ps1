# Extract text from PDF using PowerShell
# This uses a simple approach to extract text from PDF files

$pdf_path = "Z:/Rick Garner/Documentation/MoveIT/Environment Diagrams/BSOC MOVEit Environment V1.08 09.07.2023.pdf"

# Check if file exists
if (-not (Test-Path $pdf_path)) {
    Write-Host "Error: PDF file not found at $pdf_path" -ForegroundColor Red
    exit 1
}

Write-Host "Reading PDF file: $pdf_path" -ForegroundColor Cyan
Write-Host ""

# Try to extract text using PowerShell's built-in capabilities
# PDF text extraction is limited without external libraries
# We'll use a workaround: copy the PDF to a temp location and try to extract

$temp_dir = "C:\Temp\MoveIT_PDF_Extract"
if (-not (Test-Path $temp_dir)) {
    New-Item -ItemType Directory -Path $temp_dir -Force | Out-Null
}

# Copy PDF to temp location
$temp_pdf = Join-Path $temp_dir "BSOC_MOVEit_Environment.pdf"
Copy-Item $pdf_path $temp_pdf -Force

Write-Host "PDF copied to: $temp_pdf" -ForegroundColor Gray
Write-Host ""

# Try to use Microsoft Word to extract text (if available)
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open($temp_pdf)
    $full_text = $doc.Content.Text
    $doc.Close($false)
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    
    Write-Host "Successfully extracted text using Word COM" -ForegroundColor Green
} catch {
    Write-Host "Word COM extraction failed: $_" -ForegroundColor Yellow
    Write-Host "Trying alternative method..." -ForegroundColor Gray
    
    # Alternative: Try to read raw PDF text (limited success)
    try {
        $bytes = [System.IO.File]::ReadAllBytes($temp_pdf)
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        
        # Extract text streams from PDF (PDFs store text in streams)
        $pattern = r'BT\s((?:[^B]|B(?![^T]))*?[^T]ET)'
        $matches = [regex]::Matches($text, $pattern)
        
        $full_text = ""
        foreach ($match in $matches) {
            $full_text += $match.Groups[1].Value + "`n"
        }
        
        if ([string]::IsNullOrWhiteSpace($full_text)) {
            Write-Host "Could not extract meaningful text from PDF" -ForegroundColor Yellow
            $full_text = "PDF text extraction failed - PDF may be image-based or encrypted"
        } else {
            Write-Host "Extracted text from PDF streams" -ForegroundColor Green
        }
    } catch {
        Write-Host "Alternative extraction failed: $_" -ForegroundColor Red
        $full_text = "PDF text extraction failed"
    }
}

# Clean up temp file
if (Test-Path $temp_pdf) {
    Remove-Item $temp_pdf -Force
}

# Extract IP addresses
$ip_pattern = '\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
$ip_addresses = [regex]::Matches($full_text, $ip_pattern) | ForEach-Object { $_.Value } | Select-Object -Unique

# Extract server names (looking for patterns like BSOAUTALB001, etc.)
$server_pattern = '\b([A-Z]{2,}[A-Z0-9]{2,})\b'
$server_names = [regex]::Matches($full_text, $server_pattern) | ForEach-Object { $_.Value } | Select-Object -Unique

# Extract domain names
$domain_pattern = '\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})\b'
$domains = [regex]::Matches($full_text, $domain_pattern) | ForEach-Object { $_.Value } | Select-Object -Unique

# Extract URLs
$url_pattern = '\b(https?://[^\s<>"{}|\\^`\[\]]+)\b'
$urls = [regex]::Matches($full_text, $url_pattern) | ForEach-Object { $_.Value } | Select-Object -Unique

# Extract email addresses
$email_pattern = '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
$emails = [regex]::Matches($full_text, $email_pattern) | ForEach-Object { $_.Value } | Select-Object -Unique

# Extract port numbers
$port_pattern = '\b(port|Port)\s*[:=]?\s*(\d{1,5})\b'
$ports = [regex]::Matches($full_text, $port_pattern, [RegexOptions]::IgnoreCase) | ForEach-Object { $_.Groups[2].Value } | Select-Object -Unique

# Extract database/server references
$db_pattern = '\b(sql|SQL|database|Database|server|Server|instance|Instance)\b'
$db_refs = [regex]::Matches($full_text, $db_pattern, [RegexOptions]::IgnoreCase).Count

Write-Host "=" * 80
Write-Host "MOVEit Environment Information Extracted from PDF" -ForegroundColor Cyan
Write-Host "=" * 80
Write-Host ""

Write-Host "IP ADDRESSES:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($ip_addresses) {
    foreach ($ip in $ip_addresses) {
        Write-Host "  $ip"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "SERVER NAMES:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($server_names) {
    foreach ($server in $server_names) {
        Write-Host "  $server"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "DOMAIN NAMES:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($domains) {
    foreach ($domain in $domains) {
        Write-Host "  $domain"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($urls) {
    foreach ($url in $urls) {
        Write-Host "  $url"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "EMAIL ADDRESSES:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($emails) {
    foreach ($email in $emails) {
        Write-Host "  $email"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "PORTS:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($ports) {
    foreach ($port in $ports) {
        Write-Host "  $port"
    }
} else {
    Write-Host "  None found" -ForegroundColor Gray
}
Write-Host ""

Write-Host "DATABASE/SERVER REFERENCES:" -ForegroundColor Yellow
Write-Host "-" * 40
Write-Host "  Count: $db_refs"
Write-Host ""

Write-Host "FULL TEXT PREVIEW:" -ForegroundColor Yellow
Write-Host "-" * 40
if ($full_text.Length -gt 2000) {
    Write-Host $full_text.Substring(0, 2000)
} else {
    Write-Host $full_text
}
Write-Host ""

# Save structured data
$output_data = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    source_file = $pdf_path
    ip_addresses = $ip_addresses
    server_names = $server_names
    domain_names = $domains
    urls = $urls
    email_addresses = $emails
    ports = $ports
    database_server_references = $db_refs
    full_text = $full_text
}

$output_path = "storage\moveit-pdf-extraction-2026-09-23.json"
$output_data | ConvertTo-Json -Depth 10 | Out-File -FilePath $output_path -Encoding utf8
Write-Host "Structured data saved to: $output_path" -ForegroundColor Green
