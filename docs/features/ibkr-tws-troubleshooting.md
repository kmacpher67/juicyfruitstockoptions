# IBKR TWS API

Key Troubleshooting Steps:
Enable API Settings: Ensure "Enable ActiveX and Socket Clients" is checked.
Disable Read-Only: Uncheck "Read-Only API" to allow orders.
Check Socket Port: Verify the port matches your application:
Live: 7496 (TWS) or 4001 (Gateway).
Paper: 7497 (TWS) or 4002 (Gateway).
Trusted IPs: If not using localhost, add your IP to the "Trusted IPs" list.
Locahost Bug: If connecting from the same machine, try checking "Allow connections from localhost only," or if that fails, try unchecking it and ensuring 127.0.0.1 is in Trusted IPs.
Restart/Relogin: If usin

If issues persist, check the TWS log file (found in C:\Jts) after setting the logging level to "Detail" under API settings.