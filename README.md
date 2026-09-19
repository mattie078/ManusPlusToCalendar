# ManusPlusToCalendar

Reads your work schedule from MyManus and writes it into Google Calendar
and/or Apple (iCloud) Calendar. Run it whenever your rota changes and your
calendar catches up: new shifts are added, changed shifts are updated in place,
and nothing is duplicated.

## Features

- Reads your schedule from MyManus for the next few weeks.
- Syncs to Google Calendar, Apple Calendar, or both. Each is optional.
- Adds your expected pay to the event description, including the Sunday
  surcharge and an optional travel allowance.
- Flags shifts that clash with unavailability, illness, holiday or vacation, and
  colours those events differently.
- Attaches real coordinates to the location so Apple Calendar shows a map pin
  and travel time.
- Safe to re-run: it updates existing events instead of creating duplicates.

## Prerequisites

- Python 3.9 or newer (developed and verified on 3.12).
- A MyManus account.
- For Google Calendar: a Google Cloud project with the Calendar API enabled.
- For Apple Calendar: an iCloud account with an app-specific password.

You need **at least one** of Google or Apple, but not both.

## Setup

### Step 1: Get the code

```bash
git clone https://github.com/mattie078/ManusPlusToCalendar.git
cd ManusPlusToCalendar
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Turn on the credential guard

This repo keeps `.env` and `credentials.json` in version control as **blank
templates**, so you can see exactly which values need filling in. The risk is
that once you fill them in, a routine `git add -A` would publish your password.
One command per clone prevents that:

```bash
git config core.hooksPath .githooks
```

That enables a pre-commit hook which refuses any commit where those files
contain real values. As a second layer, also tell git to ignore your local
edits to them entirely:

```bash
git update-index --skip-worktree .env credentials.json
```

> If you ever need to change the *templates* themselves, temporarily undo that
> with `git update-index --no-skip-worktree .env credentials.json`.

### Step 4: Fill in `.env`

Open `.env` and fill in the values. Every setting is documented in the file
itself; the required ones are:

| Setting | Meaning |
| --- | --- |
| `company_name` | The part of your MyManus web address before `.manus.plus`. For `https://acme.manus.plus` this is `acme`. |
| `manus_username` | Your MyManus login. |
| `manus_password` | Your MyManus password. |
| `event_summary` | The calendar event title, e.g. `Work`. |
| `event_timezone` | A TZ database name, e.g. `Europe/Amsterdam`. |

Everything below is optional; leave it as `''` to switch the feature off.

| Setting | Meaning |
| --- | --- |
| `event_location` | Full address **including city and country**, so it can be resolved to a map pin. |
| `event_location_title` | Short name Apple Calendar shows for the place, e.g. `Main Street 1`. |
| `travel_allowance_per_km` | Money reimbursed per kilometre, e.g. `0.23`. |
| `single_ride_journey_km` | One-way distance to work. The script counts it twice, there and back. |
| `icloud_username` | Your iCloud email address. |
| `icloud_app_password` | An **app-specific** password (see step 6). |
| `icloud_calendar_name` | Which iCloud calendar to write to. Defaults to `Work`. |

The travel allowance only appears when **both** `travel_allowance_per_km` and
`single_ride_journey_km` are set. The script warns you if only one is filled in.

### Step 5: Google Calendar (optional)

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. [Enable the Google Calendar API](https://console.cloud.google.com/apis/enableflow?apiid=calendar-json.googleapis.com)
   for that project.
3. Go to **APIs & Services > Credentials**, click **Create Credentials**, and
   choose **OAuth 2.0 Client ID**. Pick **Desktop app** as the application type.
4. Configure the consent screen. While it is in "Testing" mode, add your own
   Google account under **Test users**, or sign-in will be refused.
5. Download the client secret JSON, rename it to `credentials.json`, and replace
   the blank template in this folder.
6. The first run opens a browser to authorise the app. It then writes
   `token.json`, which keeps you signed in. That file is git-ignored; delete it
   if you ever need to sign in as someone else.

To skip Google Calendar entirely, just leave `credentials.json` blank.

### Step 6: Apple / iCloud Calendar (optional)

1. Sign in at [appleid.apple.com](https://appleid.apple.com).
2. Go to **Sign-In and Security > App-Specific Passwords** and generate one.
3. Put your iCloud email in `icloud_username` and that generated password in
   `icloud_app_password`.

Your normal Apple password will **not** work here, and two-factor
authentication must be enabled on the account for app-specific passwords to
exist at all.

The calendar named in `icloud_calendar_name` must already exist in Apple
Calendar; the script will not create it. If the name does not match, the error
lists the calendars it actually found.

### Step 7: Run it

```bash
python main.py
```

You can run this from any directory; it finds its own `.env`.

## Usage

Re-run `python main.py` whenever your rota changes. It is safe to run as often
as you like:

- A shift that is not in your calendar yet is created.
- A shift whose time, pay or availability changed is updated in place.
- A shift that already matches is left alone.

Events are matched by a deterministic ID derived from the shift's start time, so
re-running never produces duplicates.

## Troubleshooting

**`Configuration problem: These required settings are still empty in .env`**
Exactly what it says: open `.env` and fill in the listed keys.

**`MyManus rejected the login (400)`**
Check `manus_username` and `manus_password`. If you have left the company, the
account is probably deactivated, and there is nothing left to sync.

**`MyManus did not return the expected account details`**
The login worked but the account has no active contract. Same likely cause.

**`No shifts found in the next N weeks`**
Not an error. There is simply nothing rostered.

**`credentials.json is still the blank template`**
Replace it with the file downloaded from Google Cloud (step 5), or leave it
blank to skip Google Calendar.

**`Could not sign in to iCloud`**
You almost certainly used your normal Apple password instead of an app-specific
one. See step 6.

**`Token has been expired for too long, please reauthenticate`**
Normal after a long gap. The script reopens the browser automatically. If it
loops, delete `token.json` and run again.

**`No coordinates found for ...`**
The address in `event_location` could not be geocoded. The location is still
added as plain text. Try including the city and country.

## License

MIT. See [LICENSE](LICENSE).
