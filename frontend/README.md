# Vietlott AI Frontend

Flutter frontend foundation for a personal Vietlott statistics and AI analysis application.

## Getting started

From this directory, install dependencies and run the app:

```bash
flutter pub get
flutter run
```

The app loads all draw and analysis data from the API; it does not ship with sample
draws. Configure the API base URL from Settings. The selected game is sent as the
`game_type` query parameter (`5_35`, `6_45`, or `6_55`) to:
`/history`, `/latest`, `/statistics`, `/pairs`, `/triplets`, and `/prediction`.
Network failures and timeouts are shown in the UI rather than silently falling back
to hardcoded values.

## Architecture

- `screens/`: UI pages
- `widgets/`: reusable presentation components
- `models/`: null-safe API models
- `services/`: HTTP communication
- `providers/`: application state
- `theme/`: Material 3 styling
- `utils/`: routes and constants
