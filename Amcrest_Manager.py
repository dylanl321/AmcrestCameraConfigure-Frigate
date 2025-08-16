#!/usr/bin/env python3
"""
Amcrest Camera Manager - Comprehensive tool for managing Amcrest/Dahua cameras via Frigate.

This script provides functionality for:
- NTP time synchronization
- Timestamp overlay configuration
- Camera discovery and status checking
- Bulk configuration management

Usage:
    python amcrest_manager.py --frigate-url <url> <command> [options]

Commands:
    ntp-sync          - Configure NTP settings and sync time
    timestamp-config  - Configure timestamp overlay settings
    status           - Check camera status and configuration
    discover         - Discover cameras from Frigate configuration
"""

import requests
import sys
import argparse
import re
from datetime import datetime
from requests.auth import HTTPDigestAuth
from urllib.parse import urlparse

class AmcrestCamera:
    def __init__(self, host, user, password, https=False, verify_tls=True, timeout=10):
        self.base = f"{'https' if https else 'http'}://{host}"
        self.auth = HTTPDigestAuth(user, password)
        self.verify = verify_tls
        self.timeout = timeout

    def _get(self, path, params=None):
        url = f"{self.base}{path}"
        resp = requests.get(url, params=params, auth=self.auth, timeout=self.timeout, verify=self.verify)
        resp.raise_for_status()
        return resp

    def get_current_time(self):
        """Get current time from camera."""
        try:
            r = self._get("/cgi-bin/global.cgi", {"action": "getCurrentTime"})
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def set_current_time(self, time_str):
        """Set current time on camera."""
        try:
            r = self._get("/cgi-bin/global.cgi", {"action": "setCurrentTime", "time": time_str})
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def get_ntp_config(self):
        """Get NTP configuration."""
        try:
            r = self._get("/cgi-bin/configManager.cgi", {"action": "getConfig", "name": "NTP"})
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def set_ntp_config(self, server, port=123, enable=True, update_period=60):
        """Set NTP configuration."""
        try:
            params = {
                "action": "setConfig",
                "NTP.Address": server,
                "NTP.Port": str(port),
                "NTP.Enable": "true" if enable else "false",
                "NTP.UpdatePeriod": str(update_period),
            }
            r = self._get("/cgi-bin/configManager.cgi", params=params)
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def get_timestamp_config(self):
        """Get timestamp configuration."""
        try:
            r = self._get("/cgi-bin/configManager.cgi", {"action": "getConfig", "name": "VideoWidget"})
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def enable_timestamp(self):
        """Enable timestamp overlay."""
        try:
            params = {
                "action": "setConfig",
                "VideoWidget[0].TimeTitle.EncodeBlend": "true",
                "VideoWidget[0].TimeTitle.PreviewBlend": "true",
            }
            r = self._get("/cgi-bin/configManager.cgi", params=params)
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def set_timestamp_position(self, position="tl"):
        """Set timestamp position."""
        try:
            positions = {
                "tl": (87, 233, 2708, 671),    # top-left
                "tr": (2708, 233, 87, 671),    # top-right
                "bl": (87, 671, 2708, 233),    # bottom-left
                "br": (2708, 671, 87, 233),    # bottom-right
            }
            
            if position not in positions:
                return "Invalid position. Use: tl, tr, bl, br"
            
            x1, y1, x2, y2 = positions[position]
            
            params = {
                "action": "setConfig",
                "VideoWidget[0].TimeTitle.Rect[0]": str(x1),
                "VideoWidget[0].TimeTitle.Rect[1]": str(y1),
                "VideoWidget[0].TimeTitle.Rect[2]": str(x2),
                "VideoWidget[0].TimeTitle.Rect[3]": str(y2),
            }
            
            r = self._get("/cgi-bin/configManager.cgi", params=params)
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def enable_day_of_week(self):
        """Enable day of week display."""
        try:
            params = {
                "action": "setConfig",
                "VideoWidget[0].TimeTitle.ShowWeek": "true",
                "VideoWidget[0].TimeTitle.WeekPosition": "Right",
            }
            r = self._get("/cgi-bin/configManager.cgi", params=params)
            return r.text
        except Exception as e:
            return f"Error: {e}"

    def set_time_format_12h(self):
        """Try to set 12-hour time format."""
        try:
            params = {
                "action": "setConfig",
                "Local.TimeFormat": "12Hour",
            }
            r = self._get("/cgi-bin/configManager.cgi", params=params)
            return r.text
        except Exception as e:
            return f"Error: {e}"

def fetch_frigate_config(base_url, headers=None, timeout=10, verify=True):
    """Fetch configuration from Frigate."""
    url = base_url.rstrip("/") + "/api/config"
    r = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.json()

def fetch_frigate_raw_config(base_url, headers=None, timeout=10, verify=True):
    """Fetch raw YAML configuration from Frigate."""
    url = base_url.rstrip("/") + "/api/config/raw"
    r = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.text

def collect_cameras_from_frigate(cfg_json, go2rtc_json=None, include_filters=None, raw_config=None):
    """Collect camera information from Frigate configuration."""
    host_map = {}
    
    # Process cameras from main config
    for cam_name, cam_data in cfg_json.get("cameras", {}).items():
        if include_filters and not any(filt in cam_name for filt in include_filters):
            continue
            
        # Check ffmpeg inputs for RTSP URLs
        ffmpeg_inputs = cam_data.get("ffmpeg", {}).get("inputs", [])
        for input_data in ffmpeg_inputs:
            rtsp_path = input_data.get("path", "")
            if rtsp_path.startswith("rtsp://"):
                # Extract RTSP URL
                rtsp_match = re.search(r'rtsp://([^:]+):([^@]+)@([^:\s]+):(\d+)/[^\s\n]+', rtsp_path)
                if rtsp_match:
                    user, password, host, port = rtsp_match.groups()
                    
                    if host not in host_map:
                        host_map[host] = {
                            "user": user,
                            "pass": password,
                            "source": "main_config",
                            "cams": []
                        }
                    
                    if cam_name not in host_map[host]["cams"]:
                        host_map[host]["cams"].append(cam_name)
    
    # Extract credentials from raw config if available
    if raw_config:
        try:
            rtsp_pattern = r'rtsp://([^:]+):([^@]+)@([^:\s]+):(\d+)/[^\s\n]+'
            matches = re.findall(rtsp_pattern, raw_config)
            for user, password, host, port in matches:
                if user != "*" and password != "*":
                    if host in host_map:
                        host_map[host]["user"] = user
                        host_map[host]["pass"] = password
                        host_map[host]["source"] = "raw_config"
                        print(f"✅ Found credentials for {host}: {user}:{password[:3]}***")
        except Exception as e:
            print(f"Warning: Failed to parse raw config: {e}", file=sys.stderr)
    
    return host_map

def parse_timestamp_config(config_text):
    """Parse timestamp configuration from config text."""
    config = {}
    
    lines = config_text.split('\n')
    for line in lines:
        if 'TimeTitle.' in line and '=' in line:
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()
    
    return config

def validate_ntp_server(server):
    """Validate NTP server format."""
    if not server or len(server) > 255:
        return False
    return True

def validate_time_format(time_str):
    """Validate time format (YYYY-MM-DD HH:MM:SS)."""
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False

def validate_host_reachability(host, timeout=5):
    """Validate if host is reachable."""
    try:
        import socket
        socket.create_connection((host, 80), timeout=timeout)
        return True
    except:
        return False

def ntp_sync_command(args):
    """Handle NTP sync command."""
    print("🕐 NTP Time Synchronization")
    print("=" * 50)
    
    # Fetch Frigate configuration
    headers = {"User-Agent": "Amcrest-Manager/1.0"}
    
    try:
        cfg = fetch_frigate_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched Frigate configuration")
    except Exception as e:
        print(f"❌ Failed to fetch Frigate config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Try to fetch raw config for unmasked credentials
    raw_config = None
    try:
        raw_config = fetch_frigate_raw_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched raw configuration with actual credentials")
    except Exception as e:
        print(f"⚠️  Could not fetch raw config (credentials may be masked): {e}", file=sys.stderr)
    
    # Collect cameras
    host_map = collect_cameras_from_frigate(cfg, include_filters=args.include, raw_config=raw_config)
    
    if not host_map:
        print("❌ No cameras found in Frigate configuration")
        sys.exit(1)
    
    print(f"\nDiscovered {len(host_map)} unique host(s) from Frigate:")
    for host, data in host_map.items():
        user = data.get("user", "*")
        if user == "*" and args.default_user:
            user = args.default_user
        cred_note = "embedded creds" if data.get("user") and data.get("user") != "*" else "no creds in URL"
        print(f"  - {host} [{data['source']}], {cred_note}; cams: {', '.join(data['cams'])}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        return
    
    success_count = 0
    error_count = 0
    
    for host, data in host_map.items():
        print(f"\n[{host}] Processing...")
        
        # Determine credentials
        user = data.get("user", "*")
        password = data.get("pass", "*")
        
        if user == "*" and args.default_user:
            user = args.default_user
        if password == "*" and args.default_pass:
            password = args.default_pass
        
        if user == "*" or password == "*":
            print(f"  ❌ Skipping {host}: No credentials available")
            error_count += 1
            continue
        
        print(f"  Using user '{user}'")
        
        try:
            cam = AmcrestCamera(host, user, password, timeout=args.timeout)
            
            # Get current time
            current_time = cam.get_current_time()
            if "Error" not in current_time:
                print(f"  📅 Current time: {current_time}")
            
            # Set NTP configuration if requested
            if args.ntp_server:
                if not validate_ntp_server(args.ntp_server):
                    print(f"  ❌ Invalid NTP server: {args.ntp_server}")
                    error_count += 1
                    continue
                
                print(f"  🔧 Configuring NTP server: {args.ntp_server}")
                result = cam.set_ntp_config(
                    server=args.ntp_server,
                    port=args.ntp_port,
                    enable=args.ntp_enable,
                    update_period=args.ntp_update_period
                )
                if "Error" not in result:
                    print(f"  ✅ NTP configuration applied")
                else:
                    print(f"  ❌ NTP configuration failed: {result}")
            
            # Set current time if requested
            if args.set_now:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"  🔧 Setting current time: {now}")
                result = cam.set_current_time(now)
                if "Error" not in result:
                    print(f"  ✅ Time set successfully")
                    
                    # Verify the change
                    new_time = cam.get_current_time()
                    if "Error" not in new_time:
                        print(f"  📅 Device reports current time: {new_time}")
                else:
                    print(f"  ❌ Time setting failed: {result}")
            
            # Set specific time if requested
            elif args.set_time:
                if not validate_time_format(args.set_time):
                    print(f"  ❌ Invalid time format: {args.set_time} (use YYYY-MM-DD HH:MM:SS)")
                    error_count += 1
                    continue
                
                print(f"  🔧 Setting time: {args.set_time}")
                result = cam.set_current_time(args.set_time)
                if "Error" not in result:
                    print(f"  ✅ Time set successfully")
                else:
                    print(f"  ❌ Time setting failed: {result}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error configuring {host}: {e}")
            error_count += 1
    
    print(f"\n📊 NTP Sync Summary:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {error_count}")
    print(f"  📈 Success rate: {success_count/(success_count+error_count)*100:.1f}%")

def timestamp_config_command(args):
    """Handle timestamp configuration command."""
    print("📅 Timestamp Configuration")
    print("=" * 50)
    
    # Fetch Frigate configuration
    headers = {"User-Agent": "Amcrest-Manager/1.0"}
    
    try:
        cfg = fetch_frigate_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched Frigate configuration")
    except Exception as e:
        print(f"❌ Failed to fetch Frigate config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Try to fetch raw config for unmasked credentials
    raw_config = None
    try:
        raw_config = fetch_frigate_raw_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched raw configuration with actual credentials")
    except Exception as e:
        print(f"⚠️  Could not fetch raw config (credentials may be masked): {e}", file=sys.stderr)
    
    # Collect cameras
    host_map = collect_cameras_from_frigate(cfg, include_filters=args.include, raw_config=raw_config)
    
    if not host_map:
        print("❌ No cameras found in Frigate configuration")
        sys.exit(1)
    
    print(f"\nDiscovered {len(host_map)} unique host(s) from Frigate:")
    for host, data in host_map.items():
        user = data.get("user", "*")
        if user == "*" and args.default_user:
            user = args.default_user
        cred_note = "embedded creds" if data.get("user") and data.get("user") != "*" else "no creds in URL"
        print(f"  - {host} [{data['source']}], {cred_note}; cams: {', '.join(data['cams'])}")
    
    print(f"\n🎯 Configuration Options:")
    print(f"  - Position: {args.position} ({'top-left' if args.position == 'tl' else 'top-right' if args.position == 'tr' else 'bottom-left' if args.position == 'bl' else 'bottom-right'})")
    print(f"  - Enable day of week: {'Yes' if args.enable_day_week else 'No'}")
    print(f"  - 12-hour format: {'Yes' if args.format_12h else 'No'}")
    print(f"  - Dry run: {'Yes' if args.dry_run else 'No'}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        return
    
    success_count = 0
    error_count = 0
    
    for host, data in host_map.items():
        print(f"\n[{host}] Processing...")
        
        # Determine credentials
        user = data.get("user", "*")
        password = data.get("pass", "*")
        
        if user == "*" and args.default_user:
            user = args.default_user
        if password == "*" and args.default_pass:
            password = args.default_pass
        
        if user == "*" or password == "*":
            print(f"  ❌ Skipping {host}: No credentials available")
            error_count += 1
            continue
        
        print(f"  Using user '{user}'")
        
        try:
            cam = AmcrestCamera(host, user, password, timeout=args.timeout)
            
            # Get current configuration
            current_config = cam.get_timestamp_config()
            if "Error" in current_config:
                print(f"  ❌ Failed to get config: {current_config}")
                error_count += 1
                continue
            
            # Parse timestamp configuration
            timestamp_config = parse_timestamp_config(current_config)
            
            # Check current status
            encode_blend = timestamp_config.get("table.VideoWidget[0].TimeTitle.EncodeBlend", "false")
            preview_blend = timestamp_config.get("table.VideoWidget[0].TimeTitle.PreviewBlend", "false")
            show_week = timestamp_config.get("table.VideoWidget[0].TimeTitle.ShowWeek", "false")
            
            # Get current position coordinates
            rect_0 = timestamp_config.get("table.VideoWidget[0].TimeTitle.Rect[0]", "0")
            rect_1 = timestamp_config.get("table.VideoWidget[0].TimeTitle.Rect[1]", "0")
            
            # Determine current position
            current_position = "unknown"
            if rect_0 == "87" and rect_1 == "233":
                current_position = "top-left"
            elif rect_0 == "2708" and rect_1 == "233":
                current_position = "top-right"
            elif rect_0 == "87" and rect_1 == "671":
                current_position = "bottom-left"
            elif rect_0 == "2708" and rect_1 == "671":
                current_position = "bottom-right"
            
            print(f"  📅 Current Status:")
            print(f"    - Enabled: {'✅ Yes' if encode_blend == 'true' and preview_blend == 'true' else '❌ No'}")
            print(f"    - Position: {current_position}")
            print(f"    - Day of week: {'✅ Yes' if show_week == 'true' else '❌ No'}")
            
            # Enable timestamp if disabled
            if encode_blend != "true" or preview_blend != "true":
                print(f"  🔧 Enabling timestamp...")
                result = cam.enable_timestamp()
                if "Error" not in result:
                    print(f"  ✅ Timestamp enabled")
                else:
                    print(f"  ❌ Failed to enable timestamp: {result}")
            
            # Set position if not already correct
            target_position = {'tl': 'top-left', 'tr': 'top-right', 'bl': 'bottom-left', 'br': 'bottom-right'}[args.position]
            if current_position != target_position:
                print(f"  🔧 Setting position to {target_position}...")
                result = cam.set_timestamp_position(args.position)
                if "Error" not in result:
                    print(f"  ✅ Position set to {target_position}")
                else:
                    print(f"  ❌ Failed to set position: {result}")
            else:
                print(f"  ✅ Position already correct ({target_position})")
            
            # Enable day of week if requested and not already enabled
            if args.enable_day_week and show_week != "true":
                print(f"  🔧 Enabling day of week...")
                result = cam.enable_day_of_week()
                if "Error" not in result:
                    print(f"  ✅ Day of week enabled")
                else:
                    print(f"  ❌ Failed to enable day of week: {result}")
            elif args.enable_day_week and show_week == "true":
                print(f"  ✅ Day of week already enabled")
            
            # Set 12-hour format if requested
            if args.format_12h:
                print(f"  🔧 Setting 12-hour format...")
                result = cam.set_time_format_12h()
                if "Error" not in result:
                    print(f"  ✅ 12-hour format enabled")
                else:
                    print(f"  ⚠️  12-hour format setting failed: {result}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error configuring {host}: {e}")
            error_count += 1
    
    print(f"\n📊 Timestamp Configuration Summary:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  ❌ Failed: {error_count}")
    print(f"  📈 Success rate: {success_count/(success_count+error_count)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n🎉 Timestamp configuration completed!")
        print(f"  - All cameras now have timestamps enabled")
        print(f"  - All timestamps positioned at: {args.position}")
        if args.enable_day_week:
            print(f"  - Day of week enabled on all cameras")
        if args.format_12h:
            print(f"  - 12-hour format enabled (where supported)")
        print(f"  - Check your camera feeds to see the updated timestamp format")

def status_command(args):
    """Handle status check command."""
    print("📊 Camera Status Check")
    print("=" * 50)
    
    # Fetch Frigate configuration
    headers = {"User-Agent": "Amcrest-Manager/1.0"}
    
    try:
        cfg = fetch_frigate_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched Frigate configuration")
    except Exception as e:
        print(f"❌ Failed to fetch Frigate config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Try to fetch raw config for unmasked credentials
    raw_config = None
    try:
        raw_config = fetch_frigate_raw_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched raw configuration with actual credentials")
    except Exception as e:
        print(f"⚠️  Could not fetch raw config (credentials may be masked): {e}", file=sys.stderr)
    
    # Collect cameras
    host_map = collect_cameras_from_frigate(cfg, include_filters=args.include, raw_config=raw_config)
    
    if not host_map:
        print("❌ No cameras found in Frigate configuration")
        sys.exit(1)
    
    print(f"\nDiscovered {len(host_map)} unique host(s) from Frigate:")
    for host, data in host_map.items():
        user = data.get("user", "*")
        if user == "*" and args.default_user:
            user = args.default_user
        cred_note = "embedded creds" if data.get("user") and data.get("user") != "*" else "no creds in URL"
        print(f"  - {host} [{data['source']}], {cred_note}; cams: {', '.join(data['cams'])}")
    
    print(f"\n🔍 Checking camera status...")
    
    status_data = {}
    
    for host, data in host_map.items():
        print(f"\n[{host}] Checking status...")
        
        # Determine credentials
        user = data.get("user", "*")
        password = data.get("pass", "*")
        
        if user == "*" and args.default_user:
            user = args.default_user
        if password == "*" and args.default_pass:
            password = args.default_pass
        
        if user == "*" or password == "*":
            print(f"  ❌ Skipping {host}: No credentials available")
            continue
        
        print(f"  Using user '{user}'")
        
        try:
            cam = AmcrestCamera(host, user, password, timeout=args.timeout)
            
            # Get current time
            current_time = cam.get_current_time()
            if "Error" not in current_time:
                print(f"  📅 Current time: {current_time}")
            
            # Get NTP configuration
            ntp_config = cam.get_ntp_config()
            if "Error" not in ntp_config:
                print(f"  🕐 NTP configuration available")
            
            # Get timestamp configuration
            timestamp_config = cam.get_timestamp_config()
            if "Error" not in timestamp_config:
                parsed_config = parse_timestamp_config(timestamp_config)
                
                # Check timestamp status
                encode_blend = parsed_config.get("table.VideoWidget[0].TimeTitle.EncodeBlend", "false")
                preview_blend = parsed_config.get("table.VideoWidget[0].TimeTitle.PreviewBlend", "false")
                show_week = parsed_config.get("table.VideoWidget[0].TimeTitle.ShowWeek", "false")
                
                # Get position coordinates
                rect_0 = parsed_config.get("table.VideoWidget[0].TimeTitle.Rect[0]", "0")
                rect_1 = parsed_config.get("table.VideoWidget[0].TimeTitle.Rect[1]", "0")
                
                # Determine position
                position = "unknown"
                if rect_0 == "87" and rect_1 == "233":
                    position = "top-left"
                elif rect_0 == "2708" and rect_1 == "233":
                    position = "top-right"
                elif rect_0 == "87" and rect_1 == "671":
                    position = "bottom-left"
                elif rect_0 == "2708" and rect_1 == "671":
                    position = "bottom-right"
                
                print(f"  📅 Timestamp Status:")
                print(f"    - Enabled: {'✅ Yes' if encode_blend == 'true' and preview_blend == 'true' else '❌ No'}")
                print(f"    - Position: {position}")
                print(f"    - Day of week: {'✅ Yes' if show_week == 'true' else '❌ No'}")
                
                status_data[host] = {
                    "time": current_time,
                    "timestamp_enabled": encode_blend == "true" and preview_blend == "true",
                    "position": position,
                    "day_of_week": show_week == "true"
                }
            else:
                print(f"  ❌ Failed to get timestamp config: {timestamp_config}")
            
        except Exception as e:
            print(f"  ❌ Error checking {host}: {e}")
    
    # Summary
    if status_data:
        print(f"\n📊 Status Summary:")
        total_count = len(status_data)
        timestamp_enabled = sum(1 for data in status_data.values() if data["timestamp_enabled"])
        day_of_week_enabled = sum(1 for data in status_data.values() if data["day_of_week"])
        
        print(f"  📹 Total cameras: {total_count}")
        print(f"  ✅ Timestamp enabled: {timestamp_enabled}")
        print(f"  📅 Day of week enabled: {day_of_week_enabled}")
        print(f"  📈 Timestamp enabled rate: {timestamp_enabled/total_count*100:.1f}%")

def discover_command(args):
    """Handle camera discovery command."""
    print("🔍 Camera Discovery")
    print("=" * 50)
    
    # Fetch Frigate configuration
    headers = {"User-Agent": "Amcrest-Manager/1.0"}
    
    try:
        cfg = fetch_frigate_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched Frigate configuration")
    except Exception as e:
        print(f"❌ Failed to fetch Frigate config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Try to fetch raw config for unmasked credentials
    raw_config = None
    try:
        raw_config = fetch_frigate_raw_config(args.frigate_url, headers=headers, verify=not args.insecure_frigate, timeout=args.timeout)
        print("✅ Successfully fetched raw configuration with actual credentials")
    except Exception as e:
        print(f"⚠️  Could not fetch raw config (credentials may be masked): {e}", file=sys.stderr)
    
    # Collect cameras
    host_map = collect_cameras_from_frigate(cfg, include_filters=args.include, raw_config=raw_config)
    
    if not host_map:
        print("❌ No cameras found in Frigate configuration")
        sys.exit(1)
    
    print(f"\n📹 Discovered {len(host_map)} unique camera host(s):")
    print()
    
    for host, data in host_map.items():
        user = data.get("user", "*")
        if user == "*" and args.default_user:
            user = args.default_user
        cred_note = "embedded creds" if data.get("user") and data.get("user") != "*" else "no creds in URL"
        
        print(f"🔸 {host}")
        print(f"   📍 Source: {data['source']}")
        print(f"   🔐 Credentials: {cred_note}")
        print(f"   📷 Cameras: {', '.join(data['cams'])}")
        print()

def main():
    parser = argparse.ArgumentParser(
        description="Amcrest Camera Manager - Comprehensive tool for managing Amcrest/Dahua cameras via Frigate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check camera status
  python amcrest_manager.py --frigate-url http://10.0.1.66:5000 status

  # Configure NTP and sync time
  python amcrest_manager.py --frigate-url http://10.0.1.66:5000 ntp-sync --ntp-server pool.ntp.org --set-now

  # Configure timestamps with day of week
  python amcrest_manager.py --frigate-url http://10.0.1.66:5000 timestamp-config --enable-day-week

  # Discover cameras
  python amcrest_manager.py --frigate-url http://10.0.1.66:5000 discover
        """
    )
    
    # Global arguments
    parser.add_argument("--frigate-url", required=True, help="Frigate base URL")
    parser.add_argument("--default-user", help="Default username for cameras")
    parser.add_argument("--default-pass", help="Default password for cameras")
    parser.add_argument("--include", nargs="*", help="Only process cameras containing these strings")
    parser.add_argument("--insecure-frigate", action="store_true", help="Skip SSL verification for Frigate")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # NTP sync command
    ntp_parser = subparsers.add_parser("ntp-sync", help="Configure NTP settings and sync time")
    ntp_parser.add_argument("--ntp-server", help="NTP server address")
    ntp_parser.add_argument("--ntp-port", type=int, default=123, help="NTP server port")
    ntp_parser.add_argument("--ntp-enable", action="store_true", help="Enable NTP synchronization")
    ntp_parser.add_argument("--ntp-update-period", type=int, default=60, help="NTP update period in minutes")
    ntp_parser.add_argument("--set-now", action="store_true", help="Set current system time")
    ntp_parser.add_argument("--set-time", help="Set specific time (YYYY-MM-DD HH:MM:SS)")
    ntp_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    # Timestamp config command
    timestamp_parser = subparsers.add_parser("timestamp-config", help="Configure timestamp overlay settings")
    timestamp_parser.add_argument("--position", choices=["tl", "tr", "bl", "br"], default="tl", 
                                 help="Timestamp position (default: tl)")
    timestamp_parser.add_argument("--enable-day-week", action="store_true", help="Enable day of week display")
    timestamp_parser.add_argument("--format-12h", action="store_true", help="Set 12-hour time format")
    timestamp_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check camera status and configuration")
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover cameras from Frigate configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == "ntp-sync":
        ntp_sync_command(args)
    elif args.command == "timestamp-config":
        timestamp_config_command(args)
    elif args.command == "status":
        status_command(args)
    elif args.command == "discover":
        discover_command(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
