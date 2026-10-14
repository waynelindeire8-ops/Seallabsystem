# Lab Software dashboard redesign

The supplied Flask application has been restyled to closely match the provided reference image. The shared shell now uses a blue Lab Software header, welcome user menu, light left navigation rail, breadcrumb bar, reference-style page heading, flat bordered cards, circular colored metric icons, a two-column metric grid, and a Recent Patients panel. Navigation remains connected to the existing routes, with collapsible Manage Tests, Manage Stock, and Other sections plus a reversible sidebar collapse control.

The dashboard API now supplies real counts for total tests, clinics, test parameters, specimens, patients, and products from the existing SQLite schema. Existing authentication, patient navigation, sample management, forms, reports, and other routes remain in place. The login screen was also updated to use the same visual language.

## Local launch

```bash
cd seallabsystem
sudo pip3 install -r requirements.txt
python3 run.py
```

Open `http://127.0.0.1:5000/auth/login` and use the seeded development account `admin` / `admin123` if the database has not been changed.

## Verification

Python syntax checks passed. The login page, authenticated dashboard, patient management view, dashboard API, navigation submenus, and sidebar collapse control were exercised locally. The browser console reported no JavaScript errors during verification.

## Imported archive data

The `seal.rar` archive was a legacy MySQL/MyISAM database snapshot. Only the `product_clients` table contained row data; the other archived tables contained definitions without data files. Two client records were recovered and imported into the current `clients` table: **Bix Technologies** was imported as active, and **cccccccccc** was imported as inactive because the source row was marked deleted. The import created a timestamped database backup before writing and was verified in the Clinics page and dashboard count.
