# **Infrastructure Setup: Ubuntu to Google Drive Automation**
**Primary User:** Ken MacPherson  
**System:** Ubuntu (ThinkPad-P53)  
**Project:** `juicy-fuits-stock-app`  
**Target Folder ID:** `143kk-X98X-JBuA-73ZI9GfpOrX3fvKok`

---

## **1. Environment Configuration**
These commands ensure the `gcloud` CLI is updated via the official APT repository and correctly pointed at your trading dashboard project.

```bash
# Update gcloud to ensure latest features
sudo apt-get update && sudo apt-get install google-cloud-cli

# Set the project context
gcloud config set project juicy-fuits-stock-app

# Enable the necessary API (One-time)
gcloud services enable drive.googleapis.com
```

---

## **2. The OAuth "Access Blocked" Protocol**
If you see **Error 403: access_denied** or **"This app is blocked,"** follow these steps in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent):

1.  **User Type:** Ensure it is set to "External."
2.  **Publishing Status:** Set to "Testing."
3.  **Test Users (CRITICAL):** You must add `kmacpher67@gmail.com` to the "Test Users" list. Even as the owner, you are not exempt from this whitelist while in testing mode.
4.  **Credentials:** Use a "Desktop App" OAuth Client ID.

---

## **3. Master Authentication Command**
Use this specific command to refresh your local credentials. Using a custom `client_id-file` bypasses the standard gcloud restrictions for sensitive Drive scopes.

```bash
gcloud auth application-default login \
  --client-id-file=client_secret.json \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive"
```
**Bypass Note:** When the browser opens, click **Advanced** -> **Go to Unbuntu-Juicy-mongo-backup (unsafe)** -> **Check the Drive permission box** -> **Continue**.

---

## **4. Automation Integration**
For your software (like the "Juicy Fruit" dashboard) to interact with Drive, add this environment variable to your `.bashrc` or your `.venv/bin/activate` script:

```bash
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth application-default print-access-token"
```

### **Pushing Backups via Curl**
This scriptable command uploads a file directly to your specified folder:

```bash
# Fetch fresh token
TOKEN=$(gcloud auth application-default print-access-token)

# Execute Multipart Upload
curl -X POST -L \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={name : 'mongo_backup_$(date +%F).gz', parents : ['143kk-X98X-JBuA-73ZI9GfpOrX3fvKok']};type=application/json" \
  -F "file=@/path/to/your/backup.gz" \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
```

---

## **5. Troubleshooting Checklist**
* **Token Invalid?** Re-run the `gcloud auth application-default login` command in Step 3.
* **Scope Error?** Ensure the `--scopes` flag includes the full `.../auth/drive` URL.
* **File too large?** If the backup exceeds 5MB, the `multipart` uploadType may fail; consider switching to `uploadType=resumable` or using `rclone`.
* **Security:** Ensure `client_secret.json` is in your `.gitignore`.

***

You’re right—the "craziness" was all that manual configuration in the Google Cloud Console that you never want to have to figure out again.

Here is the **Internal Configuration Log** that covers all the "under the hood" setup you did to make this work. Save this as `docs/oauth_infrastructure_guide.md`.

---

# **The "No-BS" Google Cloud OAuth Setup Guide**
**Project:** `juicy-fuits-stock-app`  
**Purpose:** Bypassing Google's security blocks to allow local Ubuntu scripts to write to Google Drive.

---

## **1. The "Consent Screen" Configuration**
This is the area that usually causes the "App Blocked" errors.
* **Path:** `APIs & Services` > `OAuth consent screen`
* **User Type:** Set to **External** (Gmail accounts cannot use "Internal").
* **Publishing Status:** Leave as **Testing**. 
    * *Warning:* Do **not** click "Push to Production" unless you want to go through a weeks-long security audit.
* **Test Users (The Whitelist):** You added `kmacpher67@gmail.com`. 
    * *Troubleshooting:* If you ever change accounts or add a collaborator, they **must** be added here manually or they will get a `403 Access Denied` error.

---

## **2. The "Desktop App" Credentials**
We discovered that the default `gcloud` login doesn't have the right "handshake" for Drive.
* **Path:** `APIs & Services` > `Credentials`
* **Type:** `OAuth 2.0 Client IDs` > **Desktop App**.
* **Name:** `Unbuntu-Juicy-mongo-backup`
* **The Secret File:** You downloaded the JSON file (e.g., `client_secret_XXX.json`). 
    * *Troubleshooting:* If you lose this file, you have to delete the Client ID in the console and create a new one.

---

## **3. Enabling the "Hidden" Permissions**
Even with a login, the project itself has to be "allowed" to talk to Drive.
* **Path:** `APIs & Services` > `Library`
* **Action:** Search for **"Google Drive API"** and click **Enable**.
* **Terminal command:** `gcloud services enable drive.googleapis.com`

---

## **4. Breaking the Security Wall (The "Advanced" Loop)**
When you run the login command, Google triggers a scary warning. This is the manual sequence to bypass it:
1.  Run the login command with `--client-id-file`.
2.  On the "Google hasn't verified this app" screen, click the tiny **Advanced** link on the bottom left.
3.  Click **Go to juicy-fuits-stock-app (unsafe)**.
4.  **Crucial:** On the permissions list, you must **manually check the box** next to "See, edit, create, and delete all your Google Drive files." If you just click "Continue" without checking the box, the token will be blank.

---

## **5. The Quota Project Hack**
Because this is a personal project, Google needs to know who to "bill" for the API hits (even if it's $0).
* **Command:** `gcloud auth application-default set-quota-project juicy-fuits-stock-app`
* *Why:* Without this, some `curl` commands will return a `403 Project Not Found` error.

---

## **6. Summary of Key Files**
| File | Purpose |
| :--- | :--- |
| `client_secret.json` | The "Key" that proves you own the app. |
| `~/.config/gcloud/application_default_credentials.json` | The actual "Token" generated after you finish the browser login. |


----
To install the Google Cloud CLI (gcloud) on Ubuntu for a stable, long-term automation environment, the recommended method is using the official Google Cloud APT repository. This ensures you receive updates through the standard package manager.

## 1. Install gcloud CLI

Execute the following steps in your terminal:

* **Update the package index and install dependencies:**
    ```bash
    sudo apt-get update
    sudo apt-get install apt-transport-https ca-certificates gnupg curl
    ```

* **Import the Google Cloud public key:**
    ```bash
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    ```

* **Add the gcloud CLI repo to your sources list:**
    ```bash
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    ```

* **Update and install the CLI:**
    ```bash
    sudo apt-get update && sudo apt-get install google-cloud-cli
    ```

## 2. Initialize and Authenticate
Once installed, you need to link the CLI to your Google account:
```bash
gcloud init
```
Follow the browser-based prompts to log in and select your project.

---

## 3. Using DRIVE_ACCESS_TOKEN_CMD
For automation—specifically when tools require a dynamic access token to interact with Google Drive—you can use the `print-access-token` command. 

To use this for an environment variable like `DRIVE_ACCESS_TOKEN_CMD`, you would typically structure your automation or configuration file to call:

```bash
gcloud auth print-access-token
```

**Implementation Example:**
If you are using a tool (like a Docker-based backup script or a custom Python utility) that expects a command to refresh the token, you would define it as:

```bash
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth print-access-token"
```

### Key Automation Notes:
* **Service Accounts:** For long-term server automation, avoid using your personal user login. Instead, create a **Service Account** in the Google Cloud Console, download the JSON key, and activate it using:
    `gcloud auth activate-service-account --key-file=SERVICE_ACCOUNT_KEY.json`
* **Scopes:** Ensure the authenticated account (user or service account) has the `https://www.googleapis.com/auth/drive` scope authorized if the token is specifically for Google Drive operations.

-----

It looks like you’ve got a solid list of legacy and active projects there. 

Since you are setting this up for **long-term automation** and mentioned using `DRIVE_ACCESS_TOKEN_CMD` earlier, you'll want to pick the project that is currently linked to your codebase or the one where you plan to manage your Google Drive API credentials.

### Which one to choose?

* **If this is for your current coding projects:** `gen-lang-client-0203700138` is often the default project ID created when using Gemini/Generative AI keys, so if you are working with LLMs or your "Anti-gravity" agent, that might be the one.
* **If this is for a specific app:** Projects like `social2crm` or `votermapper-302701` look like they might have specific API configurations already tied to them.
* **If you want a clean slate:** You can select **`[12]`** to create a fresh project specifically for this Ubuntu automation.

### Pro-Tip: Changing it later
Don't sweat the choice too much. If you pick one and realize you need another, you can always switch context without re-running the full init by using:

```bash
gcloud config set project PROJECT_ID
```

You said
 [12] Create a new project

Please enter numeric choice or text value (must exactly match list item):  12



Enter a Project ID. Note that a Project ID CANNOT be changed later.

Project IDs must be 6-30 characters (lowercase ASCII, digits, or

hyphens) in length and start with a lowercase letter. juicy-fuits-stock-app

Waiting for [operations/create_project.global.8590365466027911179] to finish...done.                 

Your current project has been set to: [juicy-fuits-stock-app].
----

Nice work getting **juicy-fuits-stock-app** spun up. Since you're working within your `.venv` for the trading dashboard, you're perfectly positioned to wire up that automation now.

Since you've initialized with your primary email, `gcloud auth print-access-token` will work immediately for your local testing. However, since this project is brand new, there are two quick hurdles to clear before your `DRIVE_ACCESS_TOKEN_CMD` will actually be useful for interacting with Drive.

### 1. Enable the Google Drive API
By default, new projects have almost all APIs turned off. You can enable the Drive API directly from your terminal:

```bash
gcloud services enable drive.googleapis.com
```

### 2. Configure the Token Command
You mentioned using `DRIVE_ACCESS_TOKEN_CMD`. To make this persistent in your current environment (and for your Ubuntu automation), add it to your `.bashrc` or your virtual environment's activation script:

```bash
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth print-access-token"
```

### A Quick Note on Scopes
When you ran `gcloud init`, it authenticated you with a broad set of default scopes. You can verify if Drive access is included in your current session by running:

```bash
gcloud auth print-access-token --scopes="https://www.googleapis.com/auth/drive"
```

If it throws an error about insufficient scopes, you'll just need to run one more command to "expand" your local credentials to include Drive access:

```bash
gcloud auth application-default login --scopes="https://www.googleapis.com/auth/drive","https://www.googleapis.com/auth/cloud-platform"
```
----
# Blocked "this app is blocked" screen: 

That "This app is blocked" screen is a common security hurdle when you're trying to grant sensitive scopes (like full Drive access) to a newly created project that hasn't been configured for "Internal" use or verified.

Because **juicy-fuits-stock-app** is a brand new project, Google's OAuth system is protecting your account from what it perceives as an unverified third-party app—even though you're the one who created it.

### How to unblock it

You need to tell the Google Cloud Console that this project is "safe" for your own use.

1.  Go to the **[OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)** in the Google Cloud Console.
2.  Ensure your project `juicy-fuits-stock-app` is selected in the top dropdown.
3.  **User Type:** Select **Internal** (this is the best option since you are using a workspace/organization account). If "Internal" isn't an option, select **External** and set the "Publishing status" to **Testing**.
4.  **Test Users:** If you chose "External/Testing," you **must** click **+ ADD USERS** and enter your email (`kmacpher67@gmail.com`). Without this, it will remain blocked.
5.  **Save and Continue** through the rest of the screens (you don't need to add specific scopes here yet, as the CLI handles that).

---

### Alternative: Use the "Advanced" bypass
Sometimes, the screen you saw will have an "Advanced" link in small text on the bottom left. 
* Click **Advanced**.
* Click **Go to [Project Name] (unsafe)**.
* This will allow you to bypass the warning and finish the login for your personal automation.

### Try the command again
Once you've added yourself as a test user or set the app to Internal, run your command again:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive
```

After this, your `gcloud auth application-default print-access-token` command will finally have the permissions it needs to push those Mongo backups.

----
Perfect, you have your **Client ID**. Now that you've downloaded the JSON or have the ID handy, we can bridge the gap that was blocking your access earlier. 

By using your own custom Client ID during the login process, you are essentially telling Google, "I am an authorized developer of this specific app," which clears that "App Blocked" security wall.

### Step 1: Link your Client ID to your Local Login
Run this command in your terminal. When the browser opens, you should now see the name of your app (**"Ubuntu-mongo-backup2026"**) and an **"Advanced"** link that lets you proceed.

```bash
gcloud auth application-default login \
  --client-id-file=path/to/your/client_secret.json \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive
```
*(If you didn't download the JSON, you can also use `--client-id=YOUR_ID` and it will prompt for the secret, but the JSON file is much easier.)*

### Step 2: Set the Quota Project
Since this is a fresh project, the CLI needs to know which "billing account" (even if it's the free tier) to hit for API limits.
```bash
gcloud auth application-default set-quota-project juicy-fuits-stock-app
```

---

### Step 3: Test the Backup Push
Now, try your upload one more time using the token command:

```bash
TOKEN=$(gcloud auth application-default print-access-token)
FOLDER_ID="143kk-X98X-JBuA-73ZI9GfpOrX3fvKok"

curl -X POST -L \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={name : 'mongodb_backup_$(date +%F).gz', parents : ['$FOLDER_ID']};type=application/json" \
  -F "file=@path/to/your/mongodb_backup.gz" \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
```

### What's next?
Once that `curl` returns a success message (a JSON block with a file ID), you are fully operational. At that point, I will compile a **Master Automation Guide** for you that covers:
1.  **Installation & Updates:** The Ubuntu APT repo steps.
2.  **Authentication:** How to refresh this setup if your token expires.
3.  **The Script:** A clean, reusable `.sh` script that automates the Mongo backup and the Drive push in one go.

-------
# Add users to test on Oath screen

The block persists because Google’s "Sensitive Scopes" policy is extremely strict for the `.../auth/drive` scope. Even with a custom Client ID, the project is likely stuck in "Testing" mode without you being explicitly authorized as a tester.

Here is the exact sequence to break through that screen:

### 1. The "Test User" Fix (Most Likely Culprit)
Even if you are the owner, you must manually whitelist yourself while the app is in "Testing" status.
1. Go to the **[OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)**.
2. Ensure **`juicy-fuits-stock-app`** (or the project from your screenshot, `gen-lang-client-0203700138`) is selected.
3. Scroll down to the **Test users** section.
4. Click **+ ADD USERS** and type in **`kmacpher67@gmail.com`**.
5. Click **Save**.

### 2. The "Advanced" Bypass
Once you are added as a test user, try the login command again. When the "This app is blocked" or "Google hasn't verified this app" screen appears:
1. Look for a small link that says **Advanced**.
2. Click **Go to [Project Name] (unsafe)** at the bottom.
3. Click **Continue** or **Allow** on the permissions screen.

---

### If it STILL says "This app is blocked" (The "External" vs "Internal" Issue)
If you are using a standard `@gmail.com` account (which you are), you **cannot** set the app to "Internal." It must stay as "External."

* If the status says **"Testing"**, you **must** have your email in the "Test Users" list as described in Step 1.
* If you haven't done so, click **"Publish App"** on the OAuth consent screen. It will warn you about verification, but for personal use with your own email, it often relaxes the "Blocked" restriction for the account owner.

### 3. Verification Command
After updating the Test User list, try the most direct login command:

```bash
gcloud auth application-default login --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive"
```

**Let me know if you see the "Advanced" link now.** Once you get that token, I'll be ready to write that master setup document for you to keep in your `juicyfruitstockoptions` directory.

---
Yes, that mismatch was exactly the problem! Google’s security policies are project-specific. If you try to use a Client ID from Project A (`juicy-fuits-stock-app`) to get permissions for Project B (`gen-lang-client-...`), it will trigger a block every time.

Now that you have the correct Client ID and Secret for **`juicy-fuits-stock-app`**, you should be able to cross the finish line.

### 1. Download the JSON
On the screen in your screenshot, click the **Download JSON** icon (the little downward arrow next to your Client secret). Save it as `client_secret.json` in your project folder: `~/personal/juicyfruitstockoptions/`.

### 2. Final Login Attempt
Run this command, pointing to that specific file:

```bash
gcloud auth application-default login \
  --client-id-file=client_secret.json \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive"
```

**Crucial:** When the browser opens, if you see "Google hasn't verified this app," look for the **Advanced** link and then click **Go to juicy-fuits-stock-app (unsafe)**. This is normal for self-developed tools.

---

### 3. Master Document for Long-Term Reuse
Once that works, here is the document you requested to save for your future self.

## **Guide: Ubuntu MongoDB to Google Drive Automation**

### **Initial Setup (One-time)**
1.  **Install gcloud CLI:** Use the APT repository method for automatic updates.
2.  **Enable API:** `gcloud services enable drive.googleapis.com`
3.  **OAuth Consent:** Set project to "External" / "Testing" and add your email as a "Test User."
4.  **Credentials:** Create a "Desktop App" OAuth Client ID and download the JSON.

### **Environment Configuration**
Add these to your `.bashrc` or your `.venv/bin/activate`:
```bash
# Command to get a fresh token for your scripts
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth application-default print-access-token"
# Set the project context
gcloud config set project juicy-fuits-stock-app
```

### **The Backup & Upload Script (`backup_to_drive.sh`)**
```bash
#!/bin/bash
# Configuration
FOLDER_ID="143kk-X98X-JBuA-73ZI9GfpOrX3fvKok"
BACKUP_NAME="mongo_backup_$(date +%F_%H-%M).gz"
LOCAL_PATH="/tmp/$BACKUP_NAME"

# 1. Create MongoDB Backup (assuming Docker or local mongo)
# Replace with your specific mongodump command
mongodump --archive=$LOCAL_PATH --gzip

# 2. Get Fresh Token
TOKEN=$(gcloud auth application-default print-access-token)

# 3. Upload to Google Drive
curl -X POST -L \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={name : '$BACKUP_NAME', parents : ['$FOLDER_ID']};type=application/json" \
  -F "file=@$LOCAL_PATH" \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"

# 4. Cleanup
rm $LOCAL_PATH
```

----
# Add yourself as a tester: 

This specific screen is actually a good sign—it means the **Client ID** is working, but Google is enforcing the "Test User" gate. Since your app is in "Testing" mode, it refuses to let even the owner in unless they are explicitly on the whitelist.

Here is how to clear that **Error 403**:

### 1. Add yourself as a Tester
1. Go to the **[OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)**.
2. Ensure **`juicy-fuits-stock-app`** is selected in the top project dropdown.
3. Scroll down to the **Test users** section.
4. Click **+ ADD USERS**.
5. Type **`kmacpher67@gmail.com`** and click **Save**.
   * *Note: Even if you are the owner, you MUST be in this list.*

### 2. The "Advanced" Link
Now, run the `gcloud auth application-default login` command again.
1. This time, the screen should look slightly different or have an **Advanced** link.
2. Click **Advanced**.
3. Click **Go to Unbuntu-Juicy-mongo-backup (unsafe)**.
4. On the next screen, check the box to allow access to Google Drive and click **Continue**.

---

### Troubleshooting if "Advanced" is missing:
If you still don't see the "Advanced" link after adding yourself as a tester, it usually means the "Publishing Status" needs a nudge:
* On the same **OAuth Consent Screen**, look for the **Publishing status** section.
* If it says "Testing," try clicking **Publish App**. It will warn you about verification, but for a personal project used only by you, this often forces the "Advanced" link to appear so you can bypass the block.

### Verification
Once you get past that screen, run:
```bash
gcloud auth application-default print-access-token
```
If it spits out a long string starting with `ya29...`, you have successfully conquered the Google OAuth wall. 

---
# app Google hasnt verified the app. 
You're almost there! This is the "soft" block that occurs once you've successfully added yourself as a Test User. Google is just making sure you know that you are the developer.

### The Final Step:
1.  Click **Continue**.
2.  On the next screen, you will likely see checkboxes for the permissions you requested (Cloud Platform and Google Drive). **Check those boxes** to grant the app permission.
3.  Click **Continue/Allow** one last time.

---

### Verification
Back in your Ubuntu terminal, run this command to confirm the token is active:
```bash
gcloud auth application-default print-access-token
```

### The "Master Document" for your Records
Since you asked for a document to save and reuse, here is the consolidated **"Juicy Fruit Backup Protocol"**. Save this as `README_BACKUP.md` in your project folder.

## **Master Guide: Google Drive Automation via gcloud**

### **1. Setup Context**
* **Project ID:** `juicy-fuits-stock-app`
* **OAuth Client Name:** `Unbuntu-Juicy-mongo-backup`
* **Target Folder ID:** `143kk-X98X-JBuA-73ZI9GfpOrX3fvKok`

### **2. Re-Authentication (If Token Fails)**
If your script throws an "Unauthorized" error in the future, run:
```bash
gcloud auth application-default login \
  --client-id-file=client_secret.json \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive"
```

### **3. The Automation Variables**
Add these to your project's `.env` or activation script:
```bash
# Set current project
gcloud config set project juicy-fuits-stock-app

# Command used by scripts to get a fresh token
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth application-default print-access-token"
```

### **4. The One-Liner Upload (curl)**
Use this inside your backup scripts to push files to your specific Drive folder:
```bash
TOKEN=$(gcloud auth application-default print-access-token)
FILE_PATH="/path/to/your/backup.gz"

curl -X POST -L \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={name : '$(basename $FILE_PATH)', parents : ['143kk-X98X-JBuA-73ZI9GfpOrX3fvKok']};type=application/json" \
  -F "file=@$FILE_PATH" \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
```

**Does that `print-access-token` command work for you now?**

-----
# You have officially conquered the Google OAuth wall. The message `Credentials saved to file: [.../application_default_credentials.json]` is the definitive confirmation that your Ubuntu environment is now authorized to act on behalf of your Google Drive.

Since you are in your project directory (`~/personal/juicyfruitstockoptions`), I have formatted this recap as a **Markdown** file. You can simply copy the block below and save it as `docs/gcloud_drive_setup.md`.

***

# Technical Recap: GCloud & Google Drive Automation Setup
**Project:** Juicy Fruit Stock Options Dashboard  
**Host:** Ubuntu (ThinkPad-P53)  
**Date:** April 9, 2026

## 1. Core Configuration
* **Google Cloud Project:** `juicy-fuits-stock-app`
* **OAuth Client ID:** `476563347929-fuvm852drr5gk9t358u0pafhr3plvq3u.apps.googleusercontent.com`
* **Backup Folder ID:** `143kk-X98X-JBuA-73ZI9GfpOrX3fvKok`
* **Scope Authorized:** `https://www.googleapis.com/auth/drive`

## 2. The "App Blocked" Resolution
We encountered the "This app is blocked" Error 403. This was resolved by:
1.  Creating a **Desktop App** OAuth credential specifically within the `juicy-fuits-stock-app` project.
2.  Whitelisting `kmacpher67@gmail.com` as a **Test User** in the OAuth Consent Screen.
3.  Using the `--client-id-file=client_secret.json` flag to tell the CLI to use our specific "app" rather than the generic gcloud default.

## 3. Automation Environment Variables
To ensure the trading dashboard or backup scripts can always rotate tokens, the following logic is used:

```bash
# Sets the context so commands don't prompt for project selection
gcloud config set project juicy-fuits-stock-app

# Used by scripts to fetch a dynamic Bearer token
export DRIVE_ACCESS_TOKEN_CMD="gcloud auth application-default print-access-token"
```

## 4. Re-Authentication Protocol
If the token expires or the environment is moved to a new machine, run:
```bash
gcloud auth application-default login \
  --client-id-file=client_secret.json \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive"
```
*Note: Always click **"Advanced"** -> **"Go to juicy-fuits-stock-app (unsafe)"** if the verification warning appears.*

## 5. Implementation Example (MongoDB Push)
The following command pushes a local file to the designated Drive folder using the ADC token:

```bash
TOKEN=$(gcloud auth application-default print-access-token)

curl -X POST -L \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={name : 'mongo_backup_$(date +%F).gz', parents : ['143kk-X98X-JBuA-73ZI9GfpOrX3fvKok']};type=application/json" \
  -F "file=@/path/to/backup.gz" \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
```

***

**Next Step for you:** Since you're in your `.venv`, make sure `client_secret.json` is added to your `.gitignore` so it doesn't accidentally end up in a public repository!

----
# GOOGLE DOCS SECURITY and LIMITED ACCESS: 

I completely agree with your gut feeling—that "scary" sensation is your security-conscious developer brain working exactly as it should. Handing a CLI tool a scope like `.../auth/drive` is effectively giving it a "Master Key" to every single file in your account, which is overkill for simply dumping a MongoDB backup into one folder.

Here is the strategic way to lock this down so you can sleep better:

### 1. The "Sandbox" Account Strategy (Highly Recommended)
Create a dedicated "service" Gmail account (e.g., `mei.automation@gmail.com`). 
* **Isolation:** This account has zero access to your personal emails, photos, or financial documents.
* **The Shared Folder Bridge:**
    1. Create the backup folder in your **main** account.
    2. Share that folder with your **new automation account** and give it "Editor" permissions.
    3. Run all your `gcloud` setup and `curl` commands using the **new account's** credentials.
* **The Result:** Even if your Ubuntu machine is compromised, the "Master Key" only opens a secondary account that contains nothing but the shared folder.

### 2. Is there a "Single Folder" Scope?
Technically, Google has a scope called `.../auth/drive.file`.
* **The Catch:** This scope only allows the app to see and edit files **that the app itself created**. It cannot see your existing folders unless you "open" them via a specific Google-provided file picker UI, which doesn't work well for headless CLI scripts.
* **The Reality:** For raw CLI/Curl automation, `.../auth/drive` is usually required to "see" the Parent Folder ID you’re pushing to. This is why the **Sandbox Account** is the industry-standard "best practice."

### 3. Immediate "Safety" Check
If you want to revoke the "Master Key" you just created until you set up the new account:
1. Go to your **[Google Account Security - Third Party Apps](https://myaccount.google.com/connections)**.
2. Find **Unbuntu-Juicy-mongo-backup**.
3. Click **Delete all connections**.
4. This instantly nukes that `ya29...` token you generated, rendering the CLI useless until you re-authenticate.

### 4. Professional "Service Account" Path
If you want to move away from "User Logins" entirely, you can use a **Google Cloud Service Account**:
* It doesn't have a "life" or a "history." It’s just an ID (`something@project.iam.gserviceaccount.com`).
* You generate a JSON key file for it.
* You share the Drive folder with that email address just like a real person.
* **Benefit:** No browser login required. You just point your script at the key file.

**Should we pivot to setting up a Service Account for this?** It’s the "pro" way to handle this and keeps your personal `kmacpher67@gmail.com` completely out of the equation.