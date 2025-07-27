#!/bin/bash

# Local development configuration with ngrok
# Replace YOUR_NGROK_URL with your actual ngrok URL

if [ "$1" == "local" ]; then
    echo "Setting up LOCAL configuration with ngrok..."
    if [ -z "$2" ]; then
        echo "Usage: $0 local YOUR_NGROK_URL"
        echo "Example: $0 local https://abc123.ngrok.io"
        exit 1
    fi
    
    NGROK_URL=$2
    
    # Update .env for local testing
    sed -i "s|SITE_URL=.*|SITE_URL=${NGROK_URL}|" .env
    sed -i "s|FAWATERAK_WEBHOOK_URL=.*|FAWATERAK_WEBHOOK_URL=${NGROK_URL}/api/payment/webhook/fawaterak/|" .env
    
    echo "✓ Updated SITE_URL to: ${NGROK_URL}"
    echo "✓ Updated FAWATERAK_WEBHOOK_URL to: ${NGROK_URL}/api/payment/webhook/fawaterak/"
    echo ""
    echo "📋 Configure this webhook URL in your Fawaterak dashboard:"
    echo "   ${NGROK_URL}/api/payment/webhook/fawaterak/"
    echo ""
    echo "🚀 Now run: python manage.py runserver"

elif [ "$1" == "production" ]; then
    echo "Setting up PRODUCTION configuration..."
    
    # Restore production URLs
    sed -i "s|SITE_URL=.*|SITE_URL=https://api2.bookefay.com|" .env
    sed -i "s|FAWATERAK_WEBHOOK_URL=.*|FAWATERAK_WEBHOOK_URL=https://api2.bookefay.com/api/payment/webhook/fawaterak/|" .env
    
    echo "✓ Restored SITE_URL to: https://api2.bookefay.com"
    echo "✓ Restored FAWATERAK_WEBHOOK_URL to: https://api2.bookefay.com/api/payment/webhook/fawaterak/"

else
    echo "Usage: $0 [local|production] [ngrok_url]"
    echo ""
    echo "Examples:"
    echo "  $0 local https://abc123.ngrok.io"
    echo "  $0 production"
    exit 1
fi