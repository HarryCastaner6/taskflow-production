#!/bin/bash

echo "========================================"
echo "TaskFlow - Quick Deployment Script"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Checking git status...${NC}"
git status

echo ""
echo -e "${BLUE}2. Adding all changes...${NC}"
git add .

echo ""
echo -e "${BLUE}3. Committing changes...${NC}"
read -p "Enter commit message (or press Enter for auto-message): " commit_msg
if [ -z "$commit_msg" ]; then
    git commit -m "🚀 TaskFlow update - auto-deploy"
else
    git commit -m "$commit_msg"
fi

echo ""
echo -e "${BLUE}4. Pushing to GitHub...${NC}"
git push origin main

echo ""
echo -e "${BLUE}5. Deploying to Vercel...${NC}"
vercel --prod

echo ""
echo -e "${GREEN}========================================"
echo "Deployment Complete!"
echo "========================================${NC}"
echo ""
echo -e "${YELLOW}Your live site will be available at:"
echo "https://taskflow-production.vercel.app${NC}"
echo ""
echo "Press Enter to exit..."
read