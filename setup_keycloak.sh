#!/bin/bash
set -e

# 1. Get Admin Token
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
     -d "client_id=admin-cli" \
     -d "username=admin" \
     -d "password=admin" \
     -d "grant_type=password" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get admin token"
  exit 1
fi

echo "Admin token acquired."

# 2. Create Realm 'insurance'
curl -s -X POST "http://localhost:8080/admin/realms" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"realm": "insurance", "enabled": true}'
echo "Realm 'insurance' created (or already exists)."

# 3. Create Client 'insurance-frontend'
curl -s -X POST "http://localhost:8080/admin/realms/insurance/clients" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "clientId": "insurance-frontend",
       "publicClient": true,
       "directAccessGrantsEnabled": true,
       "redirectUris": ["http://localhost:5173/*", "http://localhost:8000/auth/callback"],
       "webOrigins": ["http://localhost:5173"],
       "standardFlowEnabled": true
     }'
echo "Client 'insurance-frontend' created."

# 4. Create User 'ola'
curl -s -X POST "http://localhost:8080/admin/realms/insurance/users" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"username": "ola", "enabled": true, "email": "ola@example.com"}'
echo "User 'ola' created."

# 5. Set Password for User 'ola'
# First get the user ID
USER_ID=$(curl -s -X GET "http://localhost:8080/admin/realms/insurance/users?username=ola" \
     -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

curl -s -X PUT "http://localhost:8080/admin/realms/insurance/users/$USER_ID/reset-password" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"type": "password", "value": "password123", "temporary": false}'
echo "Password set for user 'ola'."

echo "--------------------------------------------------"
echo "ALL KEYCLOAK CONFIGURATION COMPLETED AUTOMATICALLY!"
echo "You can now log in to http://localhost:5173"
echo "Username: ola"
echo "Password: password123"
echo "--------------------------------------------------"
