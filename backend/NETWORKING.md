# Tailscale API access

The verified Tailscale identity for this Windows laptop is:

```text
IPv4:     100.98.227.14
MagicDNS: folontino.tail6da336.ts.net
```

Both the laptop and Android phone must be connected to the same tailnet.

## Start FastAPI

From the backend directory:

```powershell
cd D:\vietlot_project\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--host 0.0.0.0` option is required so Uvicorn accepts connections on
the Tailscale interface instead of only accepting loopback connections.

## Verify on Windows

```powershell
tailscale ip -4
tailscale status
Test-NetConnection 100.98.227.14 -Port 8000
Invoke-WebRequest http://100.98.227.14:8000/api/health
```

Expected health response:

```json
{"status":"ok","database":"connected"}
```

## Verify on Android

With Tailscale enabled on the phone, open either verified endpoint in Chrome:

```text
http://100.98.227.14:8000/docs
http://folontino.tail6da336.ts.net:8000/docs
```

Test the browser before testing the APK. If neither URL works, the problem is
outside Flutter: check that both devices are online in `tailscale status`,
that the phone is authorized in the same tailnet, that TCP 8000 is listening,
and that Windows Firewall permits the Tailscale interface.

## Windows Firewall

Do not disable Windows Firewall globally. If an inbound rule is required,
create a rule limited to the Tailscale interface and tailnet address range
from an elevated PowerShell:

```powershell
New-NetFirewallRule `
  -DisplayName "Vietlott FastAPI Tailscale TCP 8000" `
  -Direction Inbound `
  -InterfaceAlias "Tailscale" `
  -Protocol TCP `
  -LocalPort 8000 `
  -RemoteAddress 100.64.0.0/10 `
  -Action Allow `
  -Profile Any
```

Inspect or remove only this rule when needed:

```powershell
Get-NetFirewallRule -DisplayName "Vietlott FastAPI Tailscale TCP 8000"
Remove-NetFirewallRule -DisplayName "Vietlott FastAPI Tailscale TCP 8000"
```

## Flutter configuration

The default Android API base URL is the verified MagicDNS hostname:

```text
http://folontino.tail6da336.ts.net:8000
```

The verified IP can be selected explicitly during a build:

```powershell
cd D:\vietlot_project\frontend
flutter build apk --debug `
  --dart-define=API_BASE_URL=http://100.98.227.14:8000
```

The Android manifest permits cleartext HTTP only for the verified MagicDNS
hostname. Use HTTPS and remove this local HTTP exception for production.
