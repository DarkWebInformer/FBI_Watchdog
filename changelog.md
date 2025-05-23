# Changelog

## [2.1.0] - 2025-05-23
### Added
- Resolved false positives showing after an initial change is detected, it would loop over and over.

---

## [2.0.2] - 2025-03-06
### Added
- Added "ns1.usssdomainseizure.com", "ns2.usssdomainseizure.com"

---

## [2.0.1] - 2025-02-25
### Added
- Added import platform to reduce false positive seizure notifications on initial check.

---

## [2.0.0] - 2025-02-21

### Major Changes
- **Switched from Chrome WebDriver to Firefox WebDriver (Geckodriver)** for better stability and Tor support.
- **Added Tor support** for `.onion` site scanning.
- **Implemented seizure detection** for `.onion` domains.
- **Improved DNS monitoring** to detect changes in `A`, `AAAA`, `CNAME`, `MX`, `NS`, `SOA`, and `TXT` records.
- **Reworked logging and console output** for better debugging.

### New Features
- **Automatic Tor connection check** before scanning `.onion` sites.
- **Unified Telegram & Discord notifications** for better alert management.
- **Added seizure screenshot capturing** for `.onion` domains.

### Code Enhancements
- **Refactored `send_request()`** to improve response handling and debugging.
- **Optimized file handling** by merging redundant functions into `load_results()`.
- **Removed unnecessary global variables** to improve modularity.

### New Dependencies
- `pysocks` (For Tor SOCKS5 proxy support)
- `beautifulsoup4` (For better HTML parsing in seizure detection)

### Removed Dependencies
- **No major removals**, but Chrome WebDriver is no longer used.

---

**🔹 Note:** This update significantly improves the efficiency, stability, and security of FBI Watchdog. Make sure to install the new dependencies by running: `pip install -r requirements.txt`

---

## [1.1.3] - 2025-02-08
### Added
- Added auto-update functionality to the script. The script will display the changes and allow you to decline the update, so that you can review the changes manually before updating.

### Other Changes
- There was a spelling mistake
- Testing the script for auto-update in prod (this repo)... 1.1.1, 1.1.2, 1.1.3

---

## [1.0.1] - 2025-02-06
### Added
- Added functionality that now detects seizure changes from jocelyn.ns.cloudflare.com, and plato.ns.cloudflare.com. These are known to be used by LEA.

---

## [1.0.0] - 2025-02-05
### Added
- Initial release with core functionalities.

---
