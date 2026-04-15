# School Fee Management System
## Setup Guide (No Coding Required)

---

## FIRST TIME SETUP (Do this once only)

### Step 1 — Install Python
1. Go to: https://www.python.org/downloads/
2. Click the big yellow "Download Python" button
3. Run the installer
4. **IMPORTANT**: Check the box that says **"Add Python to PATH"** before clicking Install
5. Click Install Now and wait for it to finish

### Step 2 — Copy this folder
- Copy the entire `school_fee_app` folder to anywhere on your computer
- Recommended: Put it on your Desktop or in Documents

---

## RUNNING THE APP (Every day)

### Double-click `START.bat`

That's it! The app will:
1. Check that everything is installed
2. Start the server
3. Open your browser automatically at `http://localhost:5000`

**If the browser doesn't open automatically**, open any browser and type: `http://localhost:5000`

### To stop the app:
Press **Ctrl + C** in the black window, then close it.

---

## HOW TO USE

### Generating a Receipt
1. Click **Receipt Generator** in the left menu
2. Select **Fee Type** (Tuition or MISC)
3. Start typing the student name — it will auto-suggest
4. Click the student from the dropdown — all fields fill automatically
5. Set date (click "Today" for today's date)
6. Select payment mode (CASH or NEFT)
7. Enter amount
8. Click **Generate Receipt**
9. Click **Download PDF Receipt** to save/print

### Adding a New Student
1. Click **New Admission** in the left menu
2. Fill in: Student Name, Father Name, Mother Name, Grade
3. Add phone numbers and fee details
4. Click **Save New Admission**
5. A Reference Number (like NA029) is assigned automatically

### Issuing a TC (Transfer Certificate)
1. Click **TC / Delete** in the left menu
2. Search for the student by name
3. Click the student to select
4. Click **Delete Student (Issue TC)**
5. Confirm — the record is deleted and logged

### Viewing All Students
- Click **Students Database** to see all students with fee details

### Viewing MISC Transactions
- Click **MISC Sheet** to see MISC fee summary and history

### Dashboard
- Click **Dashboard** for a summary of all activity

---

## WHERE ARE THE RECEIPTS SAVED?

Receipts are saved automatically inside the app folder:
```
school_fee_app/
  receipts/
    TUITION/   ← Tuition fee PDFs
    MISC/      ← MISC fee PDFs
```

Each PDF is named like: `StudentName_ReceiptNo_Date.pdf`

---

## WHERE IS THE DATA STORED?

All data is in one file:
```
school_fee_app/database/school_fees.db
```

**Back this file up regularly!** Copy it to a USB drive or Google Drive.
To back up, just copy `school_fees.db` somewhere safe.

---

## IMPORTING YOUR EXISTING EXCEL DATA

If you want to bring your existing student data from Excel:
1. Export your Database sheet as CSV
2. Ask Claude AI to write an import script for you
3. Paste this README and the CSV structure — Claude will handle it

---

## MAKING CHANGES IN THE FUTURE

The system is designed so that future updates are easy.
When you want to:
- **Add a new field** → Tell Claude which page and what field
- **Change the receipt layout** → Show Claude the current PDF and describe changes
- **Add a new fee category** → Tell Claude what you need
- **Export data to Excel** → Ask Claude to add an export button

Just share this folder with Claude and describe what you want changed.
The code is organized so each feature is in its own file:
- `modules/students.py` — everything about students
- `modules/receipts.py` — receipt generation
- `modules/pdf_generator.py` — PDF layout
- `templates/*.html` — all the pages you see

---

## TROUBLESHOOTING

**"Python not found" error**
→ Reinstall Python and check "Add Python to PATH"

**"Port already in use" error**
→ The app is already running. Open `http://localhost:5000` in your browser.
→ Or restart your computer and try again.

**Receipt PDF not downloading**
→ Check that the `receipts/` folder exists inside the app folder.

**Data seems missing after restarting**
→ The database file is at `database/school_fees.db` — make sure it wasn't deleted.

---

## SYSTEM INFO
- Version: 1.0
- Backend: Python (Flask)
- Database: SQLite (single file, no server needed)
- PDF Engine: ReportLab
- Runs 100% offline — no internet required after setup
