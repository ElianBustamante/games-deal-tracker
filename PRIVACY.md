# Privacy policy for Steam Deal Tracker

Last updated: May 2026

Thank you for using the Steam Deal Tracker bot. This Privacy Policy outlines what information we collect, how it is used, and how you can manage or delete your data.

## 1. Information we collect

The bot only collects the minimum amount of data required to function properly. We store:

- **Discord IDs:** Your Server (Guild) ID, Channel ID, and/or your personal User ID (if you use Direct Messages).
- **Bot Configuration:** The Steam country (`/setcountry`), language (`/setlanguage`), and minimum discount percentage (`/setdiscount`) you configure.
- **Watchlist Data:** The Steam App IDs of the games you add to your watchlist (`/watchlist add`).

## 2. Information we do NOT collect

- **Message Content:** The bot does NOT read, store, or process the content of user messages. We use Discord's Slash Commands exclusively.
- **Personal Information:** We do not collect names, emails, passwords, or any identifiable personal information outside of your public Discord User ID.

## 3. How we use your information

The collected data is used strictly for:

- Routing Steam price alerts to the correct server channel or private Direct Message.
- Fetching prices from the Steam API in your preferred local currency.
- Translating the bot's responses into your preferred language.

## 4. Data sharing

We do **not** sell, rent, or share your data with any third parties under any circumstances.

## 5. Your rights & Data deletion

You have full control over your data. There are three ways your data is deleted:

- **Manual deletion (`/stop` command):** Any server admin or DM user can run `/stop` at any time to immediately wipe all their configuration and watchlist data from our database.
- **Automatic deletion on bot removal:** If the bot is kicked or removed from a Discord server, all data associated with that server is automatically deleted without any manual action required.
- **Automatic deletion after delivery failures:** If the bot is unable to deliver messages to a user's Direct Messages (e.g., the user blocked the bot), after 3 consecutive failed attempts all associated data is automatically purged.

## 6. Contact

If you have any questions or concerns regarding this Privacy Policy, please open an issue on our GitHub repository.
