#!/bin/bash
# Setup script for Waveshare 2.8" DPI LCD on SeedSigner
# Run this after flashing SeedSignerOS image

echo "=== SeedSigner DPI28 Display Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

# Backup existing config
cp /boot/config.txt /boot/config.txt.backup
echo "Backed up /boot/config.txt"

# Update dpi_output_format for correct colors
if grep -q "dpi_output_format=0x7F216" /boot/config.txt; then
    sed -i "s/dpi_output_format=0x7F216/dpi_output_format=0x7F206/" /boot/config.txt
    echo "Fixed dpi_output_format (0x7F216 -> 0x7F206)"
elif grep -q "dpi_output_format=0x7F206" /boot/config.txt; then
    echo "dpi_output_format already correct (0x7F206)"
else
    echo "dpi_output_format=0x7F206" >> /boot/config.txt
    echo "Added dpi_output_format=0x7F206"
fi

# Verify the setting
echo ""
echo "Current DPI settings:"
grep -E "dpi_output|dpi_group|dpi_mode" /boot/config.txt

echo ""
echo "=== Setup Complete ==="
echo "Reboot required for changes to take effect."
echo "Run: sudo reboot"
