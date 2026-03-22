#!/bin/bash

# Helper script to reprocess legacy IBKR trades
# This script sets the necessary environment variables for connecting to the local MongoDB.

# MongoDB Configuration (Localhost)
export MONGO_URI="mongodb://admin:admin123@localhost:27017/?authSource=admin"
export ADMIN_USER="admin"
export ADMIN_PASS="admin123"

echo "Reprocessing legacy trades from localhost MongoDB..."
echo "MONGO_URI: ${MONGO_URI}"

# Run the python script
python3 app/scripts/reprocess_legacy_trades.py

if [ $? -eq 0 ]; then
    echo "Reprocessing completed successfully."
else
    echo "Reprocessing failed. Please check the logs."
fi
