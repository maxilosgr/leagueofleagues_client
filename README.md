# League of Leagues Client

## Overview
League of Leagues is a companion application for League of Legends that allows players to register their accounts and join custom games using a password system. The application runs in the system tray and integrates with the League of Legends client.

## Features
- Account registration with Discord authentication
- Join custom games using password protection
- Real-time monitoring of the League of Legends client status
- Automatic updates notification system
- System tray integration for minimal interference with gameplay

## Installation

### Prerequisites
- Python 3.7 or higher
- League of Legends client installed
- Discord account for registration

### Setup
1. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python main.py
   ```
   
   Or use the executable if provided.

### First Use
1. Start the League of Legends client and log in
2. Locate the League of Leagues icon in your system tray (bottom right of your screen on Windows)
3. Right-click the icon and select "Register"
4. You'll need a registration code from the League of Leagues Discord bot - enter it when prompted
5. Once registered, you're ready to join games

## Usage

### Joining a Game
1. Ensure League of Legends client is running and you're logged in
2. Right-click the League of Leagues icon in the system tray
3. Click "Join Game"
4. Enter the match password provided by the game host
5. The application will automatically find and join the correct custom game lobby

### Checking Status
- Select "Check Status" from the tray icon menu to view your current connection and registration status

### Updates
- The application will automatically check for updates
- When an update is available, you'll receive a notification with download instructions

## Configuration
- Configuration is stored in your local AppData folder:
  `%LOCALAPPDATA%\LeagueOfLeagues\settings.cfg`
- This file contains your Discord authentication information
- Do not share this file with others

## Troubleshooting

### Client Not Detected
- Make sure League of Legends client is running before starting League of Leagues
- Try restarting both applications
- Ensure you have the latest version of both applications

### Registration Issues
- Verify you're using the correct registration code from the Discord bot
- Check your internet connection
- Make sure your Discord account is properly authorized with the League of Leagues service

### Join Game Failures
- Ensure the host has created the custom game correctly
- Verify you're using the correct password
- Make sure your summoner name is correctly detected (check via "Check Status")

## Support
For additional support, join the League of Leagues Discord server or contact the administrator.

## Legal
League of Leagues is not affiliated with Riot Games and is an independent third-party application.
League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc.
