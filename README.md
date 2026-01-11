# 999 Taxi Bot

Production-grade Telegram bot system for managing a Yandex Taxi park.

## Features

### Three User Roles
- **Developer**: Full system access, manage settings and admins
- **Admin**: Approve/reject registrations, broadcast messages, view statistics
- **Driver**: Register, view profile/balance/stats, withdraw money, get updates

### Core Functionality
- FSM-based driver registration with document upload
- Admin group approval/rejection workflow
- Automatic and manual data sync with Yandex Fleet API
- Daily inactive driver checks
- Multilingual support (Uzbek, Russian)
- Queue-based API throttling
- Scheduled tasks (daily sync, inactive checks)
- Dynamic settings (IDs, limits) managed from bot
- No document storage on server (all in Telegram)

## Project Structure

```
999_Taxi/
├── bot/
│   ├── handlers/           # Message and callback handlers
│   │   ├── start.py       # Start command, role detection
│   │   ├── driver.py      # Driver menu functions
│   │   ├── admin.py       # Admin panel functions
│   │   ├── developer.py   # Developer dashboard
│   │   ├── registration.py # Registration FSM flow
│   │   └── callbacks.py   # Inline button callbacks
│   ├── keyboards/         # Keyboard layouts
│   ├── states/            # FSM states
│   └── middlewares/       # Middleware (future)
├── database/              # Database layer
│   ├── models.py         # Data models
│   └── database.py       # DB operations
├── services/             # External integrations
│   ├── yandex_api.py    # Yandex Fleet API
│   ├── queue_manager.py # API throttling
│   └── scheduler.py     # Daily tasks
├── utils/               # Utilities
│   ├── messages.py     # Translations
│   └── validators.py   # Input validation
├── config/             # Configuration
│   └── settings.py    # Settings manager
├── main.py            # Entry point
├── requirements.txt   # Dependencies
└── .env              # Environment variables
```

## Installation

### 1. Clone and Setup

```bash
cd 999_Taxi
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
BOT_TOKEN=your_bot_token_here
DEVELOPER_IDS=12345678,87654321
DATABASE_PATH=taxi_bot.db

YANDEX_API_URL=https://fleet-api.taxi.yandex.net
YANDEX_PARK_ID=your_park_id
YANDEX_CLIENT_ID=your_client_id
YANDEX_API_KEY=your_api_key
YANDEX_API_SECRET=your_api_secret

PAYME_ID=your_payme_id
PAYME_KEY=your_payme_key
PAYME_URL=https://checkout.paycom.uz/api
```

### 3. Run Bot

```bash
python main.py
```

## First Time Setup

### 1. Developer Access
- Add your Telegram ID to `DEVELOPER_IDS` in `.env`
- Start the bot with `/start`
- You'll see the Developer Panel

### 2. Configure Settings
From Developer Panel:
1. Click "⚙️ Настройки"
2. Set Admin Group ID (e.g., `-1001234567890`)
3. Set Info Channel ID (e.g., `-1001234567890`)
4. Set Withdrawal Limits (e.g., `100000`)

### 3. Add Admins
From Developer Panel:
1. Click "👥 Управление админами"
2. Click "➕ Add Admin"
3. Send admin's Telegram ID

### 4. Prepare Info Channel
1. Create a channel for instructions
2. Post instruction messages
3. Get message IDs
4. Use developer dashboard to set `instruction_message_id`

## User Flows

### Developer Flow
1. `/start` → Developer Panel
2. Manage admins (add/remove by Telegram ID)
3. Configure settings (group IDs, channel IDs, limits)
4. Download logs and database backups
5. View all transactions

### Admin Flow
1. `/start` → Admin Panel
2. View statistics
3. Send broadcasts (all/active/inactive drivers)
4. Monitor pending registrations in admin group
5. Approve/reject registrations via inline buttons
6. Reply to rejection button with reason

### Driver Flow
1. `/start` → Select language (Uzbek/Russian)
2. Share phone contact
3. If new → Start registration
4. Upload documents:
   - Driver license (front/back)
   - Tech passport (front/back)
5. Wait for admin approval
6. After approval → Access main menu:
   - View profile
   - Check balance
   - View stats
   - Update info (manual sync, once per hour)
   - Withdraw money
   - Read instructions
   - Contact admins
   - Change settings (language)

## Key Features Explained

### Role Detection
```python
# config/settings.py - Developer IDs from .env
DEVELOPER_IDS = [123456, 789012]

# database - Admin IDs in DB
admin_ids = await db.get_admin_ids()

# Role hierarchy:
# 1. Developer (from .env)
# 2. Admin (from DB)
# 3. Driver (everyone else)
```

### Registration Flow
```
1. Driver sends /start
2. Selects language
3. Shares contact
4. Starts registration
5. FSM guides through 4 document steps
6. All documents sent to admin group
7. Admin clicks Approve/Reject
8. Driver gets notification
```

### Data Sync
```
Automatic: Daily at 00:00 UTC+5
Manual: Driver clicks "Update Info" (1 hour cooldown)
Queue: All sync requests go through throttled queue
API: Fetches name, callsign, car model, balance, last trip
```

### Document Storage
```
Documents are NOT stored on server
Documents stay in admin group chat
Database only stores file_id and message_id
This ensures security and saves storage
```

### Inactive Driver Detection
```
Task runs daily at 10:00 UTC+5
Finds drivers with no trips in last 7 days
Sends message with inline buttons
If driver reports problem → forwards to admin group
```

## Adding More Document Types

To add more document steps:

1. Edit `bot/states/registration.py`:
```python
class RegistrationStates(StatesGroup):
    waiting_for_driver_license_front = State()
    waiting_for_driver_license_back = State()
    waiting_for_tech_passport_front = State()
    waiting_for_tech_passport_back = State()
    waiting_for_new_document = State()  # Add new state

DOCUMENT_STEPS = [
    # ... existing steps
    ("new_document", "send_new_document", None),
]
```

2. Add message keys to `utils/messages.py`:
```python
"send_new_document": "📄 Send your new document",
```

3. Add handler in `bot/handlers/registration.py`:
```python
@router.message(RegistrationStates.waiting_for_new_document)
async def process_new_document(message: Message, state: FSMContext):
    await process_document(message, state, "new_document", None, None, is_last=True)
```

## Database Schema

### users
- `telegram_id` (PK): User's Telegram ID
- `phone`: Phone number
- `language`: uz/ru
- `role`: developer/admin/driver
- `registration_status`: not_started/in_progress/pending/approved/rejected

### drivers
- `telegram_id` (FK): Links to users
- `yandex_driver_id`: Yandex system ID
- `name`, `callsign`, `car_model`: Driver info
- `balance`: Current balance
- `last_trip_date`, `last_trip_sum`: Last trip info
- `last_sync`, `last_manual_sync`: Sync timestamps

### documents
- Links to driver
- Stores `document_type`, `file_id`, `message_id`, `chat_id`

### settings
- `key`: Setting name
- `value`: Setting value
- Dynamic configuration (admin_group_id, info_channel_id, etc.)

### transactions
- Withdrawal history
- Status tracking
- Payme integration (future)

### admin_actions
- Audit log for admin actions
- Stores who approved/rejected what

## API Integration

### Yandex Fleet API
Located in `services/yandex_api.py`:
- `get_driver_info()`: Fetch driver profile
- `get_driver_balance()`: Get current balance
- `get_driver_orders()`: Get recent trips
- `sync_driver_data()`: Update single driver
- `sync_all_drivers()`: Bulk sync (with pagination)

### Queue Manager
Located in `services/queue_manager.py`:
- Throttles API requests
- Max concurrent: 5 (configurable)
- Delay between tasks: 0.5s (configurable)
- Prevents API abuse

### Scheduler
Located in `services/scheduler.py`:
- Daily sync: 00:00 UTC+5
- Inactive check: 10:00 UTC+5
- Uses APScheduler with cron triggers

## Withdrawal System (Skeleton)

Current implementation:
1. Driver clicks "Withdraw money"
2. Shows balance and buttons
3. "Withdraw" button shows "Not implemented yet" message

To complete:
1. Add Payme API integration in `services/payme_api.py`
2. Implement card number collection FSM
3. Add amount validation
4. Create transaction in database
5. Send request to Payme
6. Handle callbacks and status updates

## Error Handling

- All exceptions logged to `bot.log`
- User-friendly error messages in both languages
- Admin notifications for critical errors
- Database transactions for data integrity

## Security Features

- Role-based access control
- Telegram ID validation
- No document storage on server
- No sensitive data in logs
- Environment variables for secrets
- Admin group ID validation

## Logs and Monitoring

### Logs
- File: `bot.log`
- Download from Developer Panel
- Contains all events, errors, API calls

### Database Backup
- Download from Developer Panel
- SQLite file with all data
- Regular backups recommended

### Transactions
- View all transactions from Developer Panel
- Track status (pending/completed/failed)
- Audit trail for withdrawals

## Troubleshooting

### Bot doesn't start
- Check `BOT_TOKEN` in `.env`
- Check `DEVELOPER_IDS` in `.env`
- Check Python version (3.9+)

### Admin group not working
- Set `admin_group_id` from Developer Panel
- Make sure bot is admin in group
- Use correct format: `-1001234567890`

### Yandex sync not working
- Check Yandex credentials in `.env`
- Check API endpoints
- Check logs for error details
- Verify park ID is correct

### Language not changing
- User must click Settings → Select language
- Language stored per user in database

## Production Deployment

### Recommended Setup
1. Use supervisor/systemd for process management
2. Set up log rotation
3. Enable database backups (daily cron)
4. Monitor logs for errors
5. Use reverse proxy if adding webhooks
6. Consider Redis for FSM storage (instead of Memory)

### Environment Variables
Minimum required:
- `BOT_TOKEN`
- `DEVELOPER_IDS`

Everything else configurable from bot!

## Support

For issues or questions:
1. Check logs (`bot.log`)
2. Review this README
3. Check code comments
4. Contact developer

## License

Proprietary - 999 Taxi Park

---

Built with ❤️ for 999 Taxi
