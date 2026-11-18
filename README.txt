MEDICONNECT - Healthcare Appointment Management System
======================================================

1. HOW TO RUN ON WINDOWS / VS CODE

   a. Extract this ZIP file.
   b. Open the extracted MediConnect folder in VS Code.
   c. Open Terminal > New Terminal.
   d. Create a virtual environment (only once):
          py -m venv venv
   e. Activate it:
          .\venv\Scripts\activate
   f. Install required packages:
          pip install -r requirements.txt
   g. Start the website:
          python app.py
   h. Open this address in your browser:
          http://127.0.0.1:5000

2. DEMO LOGIN ACCOUNTS

   ADMIN
   Email: admin@mediconnect.com
   Password: admin123

   DOCTOR 1
   Email: doctor1@mediconnect.com
   Password: doc123

   DOCTOR 2
   Email: doctor2@mediconnect.com
   Password: doc123

   DOCTOR 3
   Email: doctor3@mediconnect.com
   Password: doc123

   DOCTOR 4
   Email: doctor4@mediconnect.com
   Password: doc123

   DOCTOR 5
   Email: doctor5@mediconnect.com
   Password: doc123

   PATIENT
   Register a new patient account from the website.

3. FEATURES INCLUDED

   - Patient registration and login
   - Patient dashboard and appointment history
   - Appointment booking with doctor and time-slot selection
   - Duplicate doctor/time-slot prevention
   - Appointment cancellation
   - Doctor login and dashboard
   - Doctor can confirm, reject or complete appointments
   - Admin dashboard with patient/doctor/appointment counts
   - Admin can add and remove doctor accounts
   - Admin can update appointment status
   - In-app upcoming appointment reminders
   - Optional browser notifications for upcoming appointments
   - English, Hindi and Marathi interface labels
   - Browser voice helper for basic navigation and FAQs
   - Large readable text, clear buttons and responsive layout

4. IMPORTANT NOTES

   - The first run creates the database and demo accounts automatically.
   - If you place this project over your earlier project, keep a backup of your
     existing appointments.db. This version tries to add the new columns to
     the earlier appointments table without deleting existing appointment rows.
   - For a college demonstration, the sample passwords are acceptable.
     Do NOT use this password storage approach for a real public healthcare
     service. A production system needs password hashing, HTTPS, access
     controls, privacy safeguards and secure deployment configuration.
   - Change SECRET_KEY before deployment. Set it as an environment variable.
   - The voice helper uses browser speech features and simple predefined
     responses. It is not a medical diagnosis or treatment chatbot.
   - Use sample/demo patient information only for the college project.
