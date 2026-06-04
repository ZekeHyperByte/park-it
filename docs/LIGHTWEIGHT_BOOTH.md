# Lightweight Booth PC

Trim RAM on booth PC before running `installer/_roles/booth_pc/setup.sh`.

## OS Choice

Use **Xubuntu 24.04** instead of Ubuntu 24.04. XFCE desktop uses ~400MB vs GNOME ~800MB. Same repos, same python3.12, installer works unchanged.

## After OS Install, Before Setup Script

```bash
# Remove snap daemon (saves ~100-150MB)
sudo systemctl stop snapd
sudo apt purge -y snapd
sudo rm -rf /var/snap /snap ~/snap

# Enable zram (compressed in-RAM swap, effectively +1-2GB headroom)
sudo apt install -y zram-config
```

Both are OS-level, not touched by the project installer.

## Chrome Kiosk Tweaks

After the installer creates `~/Desktop/Parking-POS.desktop`, add extra flags to the `Exec=` line:

```
--disable-features=TranslateUI --disable-sync --disable-extensions
```

Example:

```
Exec=/usr/bin/google-chrome --app=http://10.0.0.100/pos --start-fullscreen --kiosk --disable-features=TranslateUI --disable-sync --disable-extensions
```

## Expected Result

| Before | After |
|--------|-------|
| ~1.8GB idle (Ubuntu + GNOME + snapd) | ~500-600MB idle (Xubuntu) |

Booth bridge + Chrome POS kiosk add ~400MB under load. Comfortable headroom on 4GB.
