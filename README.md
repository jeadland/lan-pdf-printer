# LAN PDF Printer

LAN PDF Printer turns a macOS machine into a LAN-visible printer that saves incoming jobs as PDFs instead of printing them.

It uses macOS's built-in `ippeveprinter` service to advertise an IPP Everywhere printer over Bonjour/DNS-SD, accepts PDF print jobs, and writes them into a folder on the host Mac. In practice, this lets a Windows 11 machine discover a printer on your local network, print to it, and have the "printed" output appear as PDFs on the Mac.

## Status

- Host OS: macOS only
- Client support: tested with Windows 11 on the same LAN
- Installer: not yet; setup is command-line based
- Scope: PDF-only job handling, no PostScript/PCL/raster conversion

## What It Does

- Advertises a printer on your local network
- Accepts IPP print jobs
- Saves each job as a PDF to a configured folder
- Runs in the foreground or as a per-user LaunchAgent
- Normalizes page order for Windows jobs that arrive with face-up ordering metadata

## Requirements

- macOS with `/usr/bin/ippeveprinter`
- Python 3.13+
- A client on the same local network
- For the tested path: Windows 11 as the printing client

## Quick Start

1. Clone the repo.
2. Copy the sample config:

   ```bash
   cp config.example.toml config.toml
   ```

3. Edit `config.toml` to choose your printer name and output folder.
4. Install the package:

   ```bash
   python3 -m pip install .
   ```

5. Verify the setup:

   ```bash
   printtopdf doctor
   ```

6. Run the printer:

   ```bash
   printtopdf run
   ```

7. On Windows 11, add the printer and send a test job.

## Configuration

The app reads `config.toml` from the project root by default. Start by copying [`config.example.toml`](/Users/joshadland/Projects/PrintToPDF/config.example.toml).

```toml
printer_name = "LAN PDF Printer"
output_dir = "~/Documents/RemotePrinterPDFs"
spool_dir = "~/Library/Application Support/PrintToPDF/spool"
port = 8631
location = "Home Office"
log_file = "~/Library/Logs/PrintToPDF/remote-printer.log"
```

Field reference:

- `printer_name`: the name users see when they add the printer
- `output_dir`: where saved PDFs are written
- `spool_dir`: temporary working directory used by the printer service
- `port`: IPP service port
- `location`: human-readable location string shown to clients
- `log_file`: JSON-lines log for service starts and saved/rejected jobs

## Commands

Check the configuration, show the IPP URI, and verify local DNS-SD visibility:

```bash
printtopdf doctor
```

Run the printer in the foreground:

```bash
printtopdf run
```

Install and load the per-user LaunchAgent:

```bash
printtopdf install-launch-agent
```

The LaunchAgent writes `~/Library/LaunchAgents/com.printtopdf.remote-printer.plist`, starts at login, and keeps the printer running for that user session.

## Windows 11 Setup

1. Open **Settings > Bluetooth & devices > Printers & scanners**.
2. Wait briefly to see whether the configured printer name appears automatically.
3. If discovery is delayed, add it manually with:

   ```text
   ipp://<your-mac-local-hostname>.local:8631/ipp/print
   ```

4. Print a test document.
5. Check `output_dir` on the Mac for the new PDF.

`printtopdf doctor` prints the exact IPP URI using the Mac's current local host name.

## Troubleshooting

### Windows says "connecting" for a long time

- Make sure the printer service is actually running on the Mac.
- Run `printtopdf doctor` and confirm DNS-SD is visible.
- Allow incoming connections for Python or Terminal if macOS prompts for firewall access.

### Windows can discover the printer but jobs do not arrive

- Confirm the Mac and Windows machine are on the same LAN.
- Check `log_file` for `job_saved` or `job_rejected` entries.
- Manually add the printer with the IPP URI if auto-discovery is flaky.

### PDFs save but page order is reversed

- Current builds normalize page order for jobs that arrive with `output-bin=face-up`.
- If you still hit this, keep the log entry and the sample PDF; that means the client is using a different ordering signal.

### The LaunchAgent is installed but not running

Use:

```bash
launchctl print gui/$(id -u)/com.printtopdf.remote-printer
```

Then inspect `log_file`.

## Architecture

- `printtopdf run` starts `ippeveprinter`
- `ippeveprinter` advertises the printer and spools incoming jobs
- a small Python hook validates the incoming document
- accepted jobs are saved into `output_dir`
- metadata is written to `log_file`

This keeps LAN PDF Printer small and uses macOS's built-in IPP tooling instead of a custom print server.

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

Run the local IPP smoke test:

```bash
RUN_IPP_TESTS=1 python3 -m unittest tests.test_integration
```

## Limitations

- macOS host only
- no GUI
- no installer yet
- PDF-only handling
- no authentication
- intended for trusted local networks
