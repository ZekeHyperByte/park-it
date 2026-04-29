#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_DESKTOP="$HOME/Desktop"
APPLICATIONS_DIR="$HOME/.local/share/applications"
ICON_DIR="$PROJECT_ROOT/assets/icons"

mkdir -p "$APPLICATIONS_DIR"

echo "=== Creating E-Parking Desktop Shortcuts ==="

# Create .desktop files
cat > "$APPLICATIONS_DIR/eparking-start.desktop" <<EOF
[Desktop Entry]
Name=E-Parking Start
Comment=Start E-Parking development environment
Exec=bash -c 'cd $PROJECT_ROOT && ./scripts/dev-start.sh && xdg-open http://localhost:3000'
Icon=$ICON_DIR/eparking-start.svg
Terminal=true
Type=Application
Categories=Development;
EOF

cat > "$APPLICATIONS_DIR/eparking-stop.desktop" <<EOF
[Desktop Entry]
Name=E-Parking Stop
Comment=Stop E-Parking development environment
Exec=$PROJECT_ROOT/scripts/dev-stop.sh
Icon=$ICON_DIR/eparking-stop.svg
Terminal=true
Type=Application
Categories=Development;
EOF

# Copy to Desktop
cp "$APPLICATIONS_DIR/eparking-start.desktop" "$USER_DESKTOP/"
cp "$APPLICATIONS_DIR/eparking-stop.desktop" "$USER_DESKTOP/"

# Mark as trusted (skip confirmation prompt)
chmod +x "$APPLICATIONS_DIR/eparking-start.desktop"
chmod +x "$APPLICATIONS_DIR/eparking-stop.desktop"
chmod +x "$USER_DESKTOP/eparking-start.desktop"
chmod +x "$USER_DESKTOP/eparking-stop.desktop"

echo "  Created: $USER_DESKTOP/E-Parking Start.desktop"
echo "  Created: $USER_DESKTOP/E-Parking Stop.desktop"
echo "  Done!"
