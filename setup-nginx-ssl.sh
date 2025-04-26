#!/bin/bash

# Set error handling
set -e
echo "🚀 Setting up Nginx and SSL for construction.contactmanagers.xyz..."

# Variables
DOMAIN="construction.contactmanagers.xyz"
NGINX_CONFIG_PATH="/etc/nginx/sites-available/$DOMAIN"
EMAIL="mazikuben2@gmail.com"  # Change this to your email for Let's Encrypt notifications

# Install Nginx if not already installed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    apt-get update
    apt-get install -y nginx
else
    echo "✅ Nginx is already installed."
fi

# Install Certbot for Let's Encrypt
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing Certbot for SSL certificates..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
else
    echo "✅ Certbot is already installed."
fi

# Create a temporary HTTP-only configuration
echo "📝 Setting up temporary HTTP configuration..."
cat > $NGINX_CONFIG_PATH << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Create symbolic link to enable the site
ln -sf $NGINX_CONFIG_PATH /etc/nginx/sites-enabled/

# Check Nginx configuration
echo "🔍 Testing Nginx configuration..."
nginx -t

# Restart Nginx to apply temporary configuration
echo "🔄 Restarting Nginx..."
systemctl restart nginx

# Obtain SSL certificate from Let's Encrypt
echo "🔒 Obtaining SSL certificate from Let's Encrypt..."
certbot --nginx --agree-tos --non-interactive --email $EMAIL -d $DOMAIN

# Apply the full configuration with SSL
echo "📝 Applying full HTTPS configuration..."
cp "./construction.contactmanagers.xyz.conf" $NGINX_CONFIG_PATH

# Check Nginx configuration again
echo "🔍 Testing final Nginx configuration..."
nginx -t

# Restart Nginx to apply final configuration
echo "🔄 Restarting Nginx with HTTPS..."
systemctl restart nginx

# Verify Nginx is running
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running correctly."
else
    echo "❌ Nginx failed to start."
    exit 1
fi

echo -e "\n🌟 Setup complete!"
echo "🔗 Your application is now accessible at:"
echo "    https://$DOMAIN"
echo "📚 API documentation at:"
echo "    https://$DOMAIN/docs"
echo "🔄 SSL certificates will auto-renew with Certbot" 