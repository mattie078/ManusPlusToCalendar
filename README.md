# ManusPlusToCalendar

ManusPlusToCalendar is a simple Python script that reads your schedule from ManusPlus and syncs it with your Google Calendar. This tool helps streamline the process of managing your schedule by automatically updating your Google Calendar with your ManusPlus workschedule.

## Features

- Read schedules from ManusPlus.
- Sync schedules with Google Calendar.
- Automatically adds location and money earnt in the description.
- Simple and easy-to-use script.

## Prerequisites

Before you can use this script, you'll need:

- Python 3.x installed on your machine.
- [A Google Cloud project with Calendar API enabled](#step-4-set-up-google-cloud-application).
- ManusPlus account credentials.

## Setup

### Step 1: Clone the repository

Clone this repository to your local machine using:

```bash
git clone https://github.com/your-username/ManusPlusToCalendar.git
cd ManusPlusToCalendar
```

### Step 2: Install dependencies

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

### Step 3: Set up environment variables

Adjust the `.env` file in the root directory of the project and add your ManusPlus credentials and Google Calendar event details. Use the provided `.env` file as a reference:

```bash
company_name=''

manus_username=''
manus_password=''

event_summary=''
event_location=''
event_timezone=''
```

### Step 4: Set up Google Cloud Application

1. Create a new project in the Google Cloud Console (https://console.cloud.google.com/).
2. Enable the Google Calendar API for your project:
   - Navigate to the API & Services > Library.
   - Search for "Google Calendar API" and enable it. (https://console.cloud.google.com/apis/enableflow?apiid=calendar-json.googleapis.com)
3. Create OAuth 2.0 credentials:
   - Go to API & Services > Credentials.
   - Click on Create Credentials and select OAuth 2.0 Client IDs.
   - Configure the consent screen to your liking.
   - Download the `credentials.json` file, rename it and place it in the root directory of your project.
4. Authorize your application:
   - Run the `main.py` script to prompt the authorization process.
   - Follow the instructions to authenticate and authorize access to your Google Calendar.

### Step 5: Run the script

After setting up the environment variables and Google Cloud credentials, you can run the script to sync your ManusPlus schedule with Google Calendar:

```bash
python sync_calendar.py
```

## Usage

Ensure your `.env` file and `credentials.json` are correctly set up. Then, simply run the script to update your Google Calendar with your ManusPlus schedule.

## Troubleshooting

If you encounter any issues, please check the following:

- Ensure your .env credentials are correct.
- Verify that the Google Calendar API is enabled for your project and check if the `credentials.json` file is correct.
- Check for any errors in the terminal output and follow the suggestions provided.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
