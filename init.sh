#!/bin/bash

# init.sh - Initialize system for Tailscale exit node
# This script configures IP forwarding required for Tailscale exit node functionality

set -e  # Exit on any error

echo "🚀 Initializing system for Tailscale exit node..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_status "Checking current IP forwarding status..."

# Check current IPv4 forwarding status
current_ipv4=$(cat /proc/sys/net/ipv4/ip_forward)
current_ipv6=$(cat /proc/sys/net/ipv6/conf/all/forwarding)

echo "Current IPv4 forwarding: $current_ipv4 (0=disabled, 1=enabled)"
echo "Current IPv6 forwarding: $current_ipv6 (0=disabled, 1=enabled)"

# Enable IP forwarding temporarily (immediate effect)
print_status "Enabling IP forwarding temporarily..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 > /dev/null

# Check if forwarding is already configured in sysctl.conf
if grep -q "^net.ipv4.ip_forward=1" /etc/sysctl.conf && grep -q "^net.ipv6.conf.all.forwarding=1" /etc/sysctl.conf; then
    print_warning "IP forwarding is already configured in /etc/sysctl.conf"
else
    print_status "Making IP forwarding permanent by adding to /etc/sysctl.conf..."
    
    # Backup sysctl.conf
    cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)
    print_status "Created backup: /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add IP forwarding configuration
    echo "" >> /etc/sysctl.conf
    echo "# Tailscale exit node configuration - added by init.sh" >> /etc/sysctl.conf
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
    
    print_success "IP forwarding configuration added to /etc/sysctl.conf"
fi

# Verify the configuration
print_status "Verifying IP forwarding configuration..."
new_ipv4=$(cat /proc/sys/net/ipv4/ip_forward)
new_ipv6=$(cat /proc/sys/net/ipv6/conf/all/forwarding)

if [[ "$new_ipv4" == "1" && "$new_ipv6" == "1" ]]; then
    print_success "IP forwarding is now enabled!"
    echo "IPv4 forwarding: $new_ipv4"
    echo "IPv6 forwarding: $new_ipv6"
else
    print_error "Failed to enable IP forwarding"
    exit 1
fi

# Check if Docker is installed and running
if command -v docker &> /dev/null; then
    print_status "Docker is installed"
    if systemctl is-active --quiet docker; then
        print_success "Docker service is running"
    else
        print_warning "Docker service is not running. You may need to start it: sudo systemctl start docker"
    fi
else
    print_warning "Docker is not installed. Please install Docker to run the Tailscale container."
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null 2>&1; then
    print_success "Docker Compose is available"
else
    print_warning "Docker Compose is not available. Please install it to use the docker-compose.yml file."
fi

# Optional: Check if .env file exists
if [[ -f ".env" ]]; then
    print_success "Found .env file"
    
    # Check for required environment variables
    required_vars=("TS_AUTHKEY" "LOCAL_SUBNET")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_warning "Missing environment variables in .env file: ${missing_vars[*]}"
        echo "Please ensure these variables are set:"
        echo "  TS_AUTHKEY=your_tailscale_auth_key"
        echo "  LOCAL_SUBNET=192.168.1.0/24  # Adjust to your network"
    fi
else
    print_warning "No .env file found. Create one with:"
    echo "  TS_AUTHKEY=your_tailscale_auth_key"
    echo "  LOCAL_SUBNET=192.168.1.0/24  # Adjust to your network"
fi

print_success "System initialization complete!"
echo ""
echo "Next steps:"
echo "1. Ensure your .env file is configured with TS_AUTHKEY and LOCAL_SUBNET"
echo "2. Run: sudo docker compose up -d tailscale"
echo "3. Check logs: sudo docker logs tailscale"
echo "4. Test exit node functionality from a client device"
echo ""
print_status "IP forwarding will persist across reboots."