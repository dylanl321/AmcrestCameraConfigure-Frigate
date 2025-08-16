# Amcrest Camera Manager

A comprehensive Python tool for managing Amcrest/Dahua cameras via Frigate. This tool provides bulk configuration capabilities for time synchronization, timestamp overlays, and camera discovery.

## 🚀 Features

- **🔍 Camera Discovery**: Automatically discover cameras from Frigate configuration
- **🕐 NTP Time Synchronization**: Configure NTP servers and sync camera time
- **📅 Timestamp Configuration**: Enable and configure timestamp overlays with day of week
- **🔐 Credential Management**: Extract credentials from Frigate's raw configuration
- **📊 Status Monitoring**: Check camera status and configuration
- **⚡ Bulk Operations**: Configure multiple cameras simultaneously

## 📋 Requirements

- Python 3.7+
- Frigate NVR instance
- Amcrest/Dahua cameras
- Network access to cameras and Frigate

## 🛠️ Installation

1. **Clone or download the project:**
   ```bash
   git clone <repository-url>
   cd Amcrest
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 📦 Dependencies

The following Python packages are required:

```
requests>=2.25.0
urllib3>=1.26.0
```

## 🎯 Usage

The tool uses a command-based interface with the following structure:

```bash
python amcrest_manager.py --frigate-url <url> <command> [options]
```

### Global Options

- `--frigate-url <url>`: **Required** - Frigate base URL (e.g., `http://10.0.1.66:5000`)
- `--default-user <username>`: Default username for cameras (if not in Frigate config)
- `--default-pass <password>`: Default password for cameras (if not in Frigate config)
- `--include <strings>`: Only process cameras containing these strings
- `--insecure-frigate`: Skip SSL verification for Frigate
- `--timeout <seconds>`: Request timeout (default: 10)

## 📖 Commands

### 🔍 Discover Cameras

Discover and list all cameras from Frigate configuration:

```bash
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 discover
```

**Output:**
```
🔍 Camera Discovery
==================================================
✅ Successfully fetched Frigate configuration
✅ Successfully fetched raw configuration with actual credentials

📹 Discovered 12 unique camera host(s):

🔸 10.0.1.145
   📍 Source: raw_config
   🔐 Credentials: embedded creds
   📷 Cameras: 140_frontdoor
```

### 📊 Check Status

Check the current status of all cameras:

```bash
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status
```

**Output:**
```
📊 Camera Status Check
==================================================
✅ Successfully fetched Frigate configuration

🔍 Checking camera status...

[10.0.1.145] Checking status...
  Using user 'admin'
  📅 Current time: 2025-01-16 11:07:54
  📅 Timestamp Status:
    - Enabled: ✅ Yes
    - Position: top-left
    - Day of week: ✅ Yes
```

### 🕐 NTP Time Synchronization

Configure NTP settings and synchronize camera time:

```bash
# Configure NTP server and sync current time
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync \
  --ntp-server pool.ntp.org \
  --ntp-enable \
  --set-now

# Set specific time
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync \
  --set-time "2025-01-16 11:07:54"

# Dry run to see what would be done
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync \
  --ntp-server pool.ntp.org \
  --dry-run
```

**NTP Options:**
- `--ntp-server <server>`: NTP server address
- `--ntp-port <port>`: NTP server port (default: 123)
- `--ntp-enable`: Enable NTP synchronization
- `--ntp-update-period <minutes>`: NTP update period (default: 60)
- `--set-now`: Set current system time
- `--set-time <time>`: Set specific time (YYYY-MM-DD HH:MM:SS)
- `--dry-run`: Show what would be done without making changes

### 📅 Timestamp Configuration

Configure timestamp overlay settings:

```bash
# Enable timestamps with day of week
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --enable-day-week

# Set timestamp position to top-right
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --position tr \
  --enable-day-week

# Enable 12-hour format (where supported)
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --format-12h \
  --enable-day-week

# Dry run to see what would be done
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --enable-day-week \
  --dry-run
```

**Timestamp Options:**
- `--position <pos>`: Timestamp position (`tl`, `tr`, `bl`, `br`)
  - `tl`: Top-left (default)
  - `tr`: Top-right
  - `bl`: Bottom-left
  - `br`: Bottom-right
- `--enable-day-week`: Enable day of week display
- `--format-12h`: Set 12-hour time format (where supported)
- `--dry-run`: Show what would be done without making changes

## 🔐 Credential Management

The tool automatically extracts camera credentials from Frigate's configuration:

1. **Primary Method**: Uses Frigate's `/api/config/raw` endpoint to get unmasked credentials
2. **Fallback Method**: Uses credentials from the main `/api/config` endpoint (may be masked)
3. **Manual Override**: Use `--default-user` and `--default-pass` for cameras without credentials

**Credential Sources:**
- `raw_config`: Credentials extracted from Frigate's raw YAML configuration
- `main_config`: Credentials from Frigate's main API (may be masked with `*`)

## 📋 Examples

### Complete Camera Setup

```bash
# 1. Discover cameras
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 discover

# 2. Check current status
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status

# 3. Configure NTP and sync time
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync \
  --ntp-server pool.ntp.org \
  --ntp-enable \
  --set-now

# 4. Configure timestamps with day of week
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --enable-day-week

# 5. Verify configuration
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status
```

### Selective Camera Configuration

```bash
# Only configure cameras with "front" in the name
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
  --include front \
  --enable-day-week

# Configure specific camera types
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync \
  --include door yard \
  --ntp-server pool.ntp.org \
  --set-now
```

### Troubleshooting

```bash
# Check camera discovery with verbose output
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 discover

# Test with insecure Frigate connection
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status \
  --insecure-frigate

# Use custom timeout for slow networks
python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status \
  --timeout 30
```

## 🔧 Configuration

### Timestamp Format

When configured with day of week enabled, cameras display timestamps like:
```
08/16/2025 11:07:54 Mon
```

Where:
- **Date and time** (24-hour format by default)
- **Day of week** (Mon, Tue, Wed, etc.) on the right side
- **Consistent position** across all camera feeds

### Position Coordinates

The tool uses predefined coordinates for timestamp positioning:

- **Top-left (tl)**: `(87, 233, 2708, 671)`
- **Top-right (tr)**: `(2708, 233, 87, 671)`
- **Bottom-left (bl)**: `(87, 671, 2708, 233)`
- **Bottom-right (br)**: `(2708, 671, 87, 233)`

## 🚨 Troubleshooting

### Common Issues

1. **"No cameras found in Frigate configuration"**
   - Verify Frigate URL is correct
   - Check that cameras are configured in Frigate
   - Ensure network connectivity to Frigate

2. **"No credentials available"**
   - Check if Frigate's raw config endpoint is accessible
   - Verify camera credentials in Frigate configuration
   - Use `--default-user` and `--default-pass` as fallback

3. **"please login first" errors**
   - Some camera models may require different authentication
   - Check camera web interface for correct credentials
   - Verify camera firmware version

4. **"Bad Request" errors**
   - Some camera models don't support all configuration options
   - Try different parameter combinations
   - Check camera documentation for supported features

### Debug Mode

For troubleshooting, you can:

1. **Use dry-run mode** to see what would be done:
   ```bash
   python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
     --enable-day-week \
     --dry-run
   ```

2. **Check individual camera status**:
   ```bash
   python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status
   ```

3. **Test with specific cameras**:
   ```bash
   python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config \
     --include problem_camera \
     --enable-day-week
   ```

## 📝 API Reference

### AmcrestCamera Class

The core class for interacting with Amcrest/Dahua cameras:

```python
cam = AmcrestCamera(host, user, password, timeout=10)

# Get current time
time = cam.get_current_time()

# Set NTP configuration
cam.set_ntp_config(server="pool.ntp.org", enable=True)

# Configure timestamp
cam.enable_timestamp()
cam.set_timestamp_position("tl")
cam.enable_day_of_week()
```

### Frigate Integration

The tool integrates with Frigate's API endpoints:

- `/api/config`: Main configuration (credentials may be masked)
- `/api/config/raw`: Raw YAML configuration (unmasked credentials)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Frigate NVR**: For providing the camera discovery and configuration API
- **Amcrest/Dahua**: For the camera API documentation and capabilities
- **Python Requests**: For the HTTP client library

## 📞 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the examples and documentation
3. Test with dry-run mode first
4. Open an issue with detailed error information

---

**Note**: This tool is designed for Amcrest/Dahua cameras and Frigate NVR. Compatibility with other camera brands or NVR systems is not guaranteed.
