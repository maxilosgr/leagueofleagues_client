# Standard library imports
import threading
import sys
import os
import time
import json
import configparser
import hashlib
import webbrowser
import asyncio
import queue
from functools import partial
import traceback

# GUI-related imports
import tkinter as tk
from tkinter import simpledialog, messagebox

# Network and API imports
import requests

# System tray icon
import pystray
from PIL import Image, ImageDraw, ImageFont

# League client connector
from lcu_driver import Connector

# Path to settings file
def get_config_path():
    """Return path to settings file in user's AppData directory."""
    try:
        # Get the AppData\Local directory path
        app_data = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'LeagueOfLeagues')
        
        # Create the directory if it doesn't exist
        if not os.path.exists(app_data):
            os.makedirs(app_data)
            
        return os.path.join(app_data, 'settings.cfg')
    except Exception as e:
        print(f"Error setting config path: {e}")
        # Fallback to current directory as last resort
        return os.path.join(os.getcwd(), 'settings.cfg')

# --------------------------
# Global variables
# --------------------------
CONFIG_PATH = get_config_path()

# API endpoints
API_BASE = "https://rust.gameras.gr"
OTP_URL = f"{API_BASE}/otp"
AUTH_URL = f"{API_BASE}/auth"
VERSION_URL = f"{API_BASE}/client_version"
DOWNLOAD_URL = f"{API_BASE}/downloadclient"
JOINMATCH_URL = f"{API_BASE}/joinmatch"
GAMEFLOW_PHASE = "/lol-gameflow/v1/gameflow-phase"

# Global application state
summoner_name = None
summoner_tag = None
region = None
is_ready = False
current_phase = None
app_icon = None  # Global reference to system tray icon
dialog_active = False  # Flag to prevent multiple dialogs
root = None  # Main Tkinter window
ui_lock = threading.Lock()  # Thread lock for UI operations
connector = None  # Will be initialized in main thread
connector_thread = None  # Thread for running connector

# --------------------------
# UI helpers
# --------------------------
def ensure_root_window():
    """Make sure we have a valid root window for dialogs."""
    global root
    
    if root is None or not root.winfo_exists():
        root = tk.Tk()
        root.title("League of Leagues")
        
        # Set it up but keep it withdrawn initially
        root.withdraw()
        
        # Center the window on screen
        center_window(root)
        
        # Make it small but not fully transparent (some systems have issues with fully transparent windows)
        root.attributes("-alpha", 0.1)  # Almost transparent but not fully
        
        # Bind protocol to handle window closing properly
        root.protocol("WM_DELETE_WINDOW", lambda: root.withdraw())
    
    return root


def center_window(window):
    """Center a tkinter window on the screen."""
    window.update_idletasks()
    
    # Get screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Get window width and height
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    
    # If window dimensions are too small (like 1x1), set reasonable defaults for centering
    if window_width < 100 or window_height < 100:
        window_width = 300
        window_height = 200
    
    # Calculate position
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Set the position
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

def show_dialog(dialog_type, title, message, parent=None):
    """Show a dialog with proper handling of the root window."""
    global root
    
    try:
        ensure_root_window()
        
        # Make sure root is deiconified and updated before showing dialog
        root.deiconify()
        root.update()
        
        # Center the root window
        center_window(root)
        
        # Show the appropriate dialog
        if dialog_type == "info":
            result = messagebox.showinfo(title, message, parent=root)
        elif dialog_type == "error":
            result = messagebox.showerror(title, message, parent=root)
        elif dialog_type == "warning":
            result = messagebox.showwarning(title, message, parent=root)
        elif dialog_type == "yesno":
            result = messagebox.askyesno(title, message, parent=root)
            return result
        
        # Hide the root window again after dialog is closed
        root.withdraw()
        return result
        
    except Exception as e:
        print(f"Error showing dialog: {e}")
        traceback.print_exc()
        # Make sure root is withdrawn in case of error
        try:
            root.withdraw()
        except:
            pass
        return None
        
def ask_for_input(title, prompt):
    """Ask the user for text input with proper window management."""
    global root
    
    try:
        ensure_root_window()
        
        # Make root visible
        root.deiconify()
        root.update()
        
        # Center the window
        center_window(root)
        
        # Get input from user
        result = simpledialog.askstring(title, prompt, parent=root)
        
        # Hide the root window again
        root.withdraw()
        return result
    except Exception as e:
        print(f"Error asking for input: {e}")
        traceback.print_exc()
        # Make sure root is withdrawn in case of error
        try:
            root.withdraw()
        except:
            pass
        return None

# --------------------------
# Config helpers
# --------------------------
def load_config():
    config = configparser.ConfigParser()
    result = {'discord_id': None}
    
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
        
        # Get Discord ID
        raw = config.get('DEFAULT', 'discord_id', fallback=None)
        try:
            result['discord_id'] = json.loads(raw).get('discord_id')
        except Exception:
            result['discord_id'] = raw.strip() if raw else None
    
    return result

def save_config(discord_id):
    config = configparser.ConfigParser()
    
    # Load existing config if it exists
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    
    # Ensure sections exist
    if 'DEFAULT' not in config:
        config['DEFAULT'] = {}
    
    # Update settings
    config['DEFAULT']['discord_id'] = discord_id
    
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)
    
    print(f"Saved config to {CONFIG_PATH}")

def delete_config():
    """Delete the configuration file."""
    try:
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
            print(f"Deleted config file: {CONFIG_PATH}")
    except Exception as e:
        print(f"Error deleting config file: {e}")

# --------------------------
# Authentication functions
# --------------------------
def authenticate(discord_id: str) -> bool:
    """Authenticate with the server using discord ID."""
    try:
        resp = requests.get(AUTH_URL, params={'discord_id': discord_id}, timeout=10)
        print(f"/auth {resp.status_code}: {resp.text}")
        
        # If we get 404 with "User not found", it means the Discord ID is not registered
        if resp.status_code == 404 and "User not found" in resp.text:
            print("User not registered, return False")
            return False
            
        return resp.status_code == 200
    except Exception as e:
        print(f"Auth error: {e}")
        return False

# --------------------------
# Menu action functions
# --------------------------
def register_action(icon, item):
    print("Register action triggered")
    global summoner_name, summoner_tag, region
    
    # Check if client is ready
    if not is_ready:
        show_dialog("error", "Not Ready", "Please open your League client first.")
        return
    
    # If we don't have summoner info, try to fetch it directly
    if not summoner_name or not summoner_tag:
        # Ask if they want to manually enter summoner info
        if show_dialog("yesno", "Summoner Info", 
                       "Could not automatically detect your summoner information. Would you like to enter it manually?"):
            
            manual_info = ask_for_input(
                "Enter Summoner Info", 
                "Enter your Summoner Name#Tag (e.g., PlayerName#NA1):"
            )
            
            if not manual_info or "#" not in manual_info:
                show_dialog("error", "Invalid Format", "Please use format: Name#Tag")
                return
            
            parts = manual_info.split('#', 1)
            summoner_name = parts[0].strip()
            summoner_tag = parts[1].strip()
        else:
            return
    
    # Display the summoner information we have
    display = f"{summoner_name}#{summoner_tag}"
    if region:
        display += f",{region}"
    
    # Ask for the OTP code directly (removing the unnecessary informational dialog)
    otp = ask_for_input(
        "Enter Registration Code", 
        f"Registering summoner: {display}\nEnter the registration code provided by the League of Leagues bot:"
    )
    
    if not otp:
        print("Registration cancelled.")
        return
        
    try:
        # Make the API request
        resp = requests.get(OTP_URL, params={'otp_pass': otp.strip(), 'summonersname': display}, timeout=10)
        print(f"/otp {resp.status_code}: {resp.text}")
        
        if resp.status_code == 200 and resp.text.strip():
            save_config(resp.text.strip())
            show_dialog("info", "Registered", "Successfully registered!")
        else:
            show_dialog("error", "Registration Failed", 
                      "Invalid registration code or server error.")
    except Exception as e:
        show_dialog("error", "Error", f"Registration failed: {str(e)}")

def join_game_action(icon, item):
    print("Join game action triggered")
    global summoner_name, summoner_tag, region
    
    # Check if client is ready
    if not is_ready or current_phase is None:
        show_dialog("error", "Error", "Client not ready or no phase info.")
        return
        
    print(f"[DEBUG] current_phase = {current_phase}")
    
    # Ask for password
    pwd = ask_for_input("Join Game", "Enter match password:")
    
    if not pwd:
        print("Join game cancelled.")
        return

    try:
        # Make the API request to join match
        resp = requests.get(JOINMATCH_URL, params={'password': pwd.strip()}, timeout=10)
        print(f"/joinmatch {resp.status_code}: {resp.text}")
        
        if resp.status_code != 200 or not resp.text:
            show_dialog("error", "Join Game", "Failed to join: Invalid response from server")
            return

        # Parse the response (format: "summonerName#TAG,REGIONpin")
        response_data = resp.text.strip()
        summoner_info, pin = response_data.split(',', 1)
        summoner_name_from_server, tag = summoner_info.split('#', 1)
        
        # Schedule the lobby join on the main thread through Tkinter's after method
        def schedule_join():
            global connector, root
            if connector and root:
                print("Scheduling join lobby operation")
                root.after(100, lambda: join_lobby(summoner_name_from_server, tag, pin))
            else:
                show_dialog("error", "Join Game", "Connector or UI not ready")
        
        # Make sure this runs on the main thread
        root.after(0, schedule_join)
        
    except Exception as e:
        show_dialog("error", "Join Game", f"Error: {str(e)}")

# Function that will be called through Tkinter's event loop (main thread)
def join_lobby(summoner, tag, pin):
    global connector, root
    
    print(f"Attempting to join lobby of {summoner}#{tag} with pin {pin}")
    
    # Create a coroutine for the lobby join
    async def do_join_lobby():
        try:
            # Get current custom games
            games_resp = await connector.request('GET', '/lol-lobby/v2/lobby/custom/available')
            games = await games_resp.json()
            
            # Find matching lobby
            match = None
            target_full = f"{summoner} #{tag}"
            
            # First try exact match
            match = next(
                (g for g in games if g.get('ownerDisplayName', '').lower() == target_full.lower()), 
                None
            )
            
            # If no exact match, try partial match
            if not match:
                match = next(
                    (g for g in games if g.get('ownerDisplayName', '').lower().startswith(
                        summoner.lower() + '#')
                    ), 
                    None
                )
            
            if not match:
                # Show error on the main thread
                root.after(0, lambda: show_dialog("error", "Join Game", 
                                               f"Couldn't find {summoner}#{tag}'s lobby"))
                return
            
            # Join the lobby
            game_id = match['id']
            endpoint = f'/lol-lobby/v2/lobby/custom/{game_id}/join'
            body = {'asSpectator': False, 'password': pin}
            
            join_resp = await connector.request('POST', endpoint, json=body)
            
            if join_resp.status == 200:
                # Show success on the main thread
                root.after(0, lambda: show_dialog("info", "Join Game", 
                                               f"Successfully joined {summoner}#{tag}'s lobby!"))
            else:
                error_msg = await join_resp.json()
                error_text = error_msg.get('message', 'Unknown error')
                # Show error on the main thread
                root.after(0, lambda: show_dialog("error", "Join Game", 
                                               f"Failed to join: {error_text}"))
        except Exception as e:
            print(f"Error in join_lobby: {e}")
            traceback.print_exc()
            # Show error on the main thread
            root.after(0, lambda: show_dialog("error", "Join Game", 
                                           f"Error during join process: {str(e)}"))
    
    # Schedule the coroutine to run in the connector's event loop
    connector._connection._loop.create_task(do_join_lobby())

def check_status_action(icon, item):
    print("Check status action triggered")
    global summoner_name, summoner_tag, region
    
    # Check registration status
    config_data = load_config()
    registered_id = config_data.get('discord_id') if isinstance(config_data, dict) else config_data
    
    status_msg = "Status:\n\n"
    status_msg += f"Client Connected: {'Yes' if is_ready else 'No'}\n"
    status_msg += f"Summoner: {summoner_name}#{summoner_tag if summoner_name and summoner_tag else 'Not detected'}\n"
    status_msg += f"Region: {region if region else 'Unknown'}\n"
    status_msg += f"Registered: {'Yes' if registered_id else 'No'}\n"
    
    show_dialog("info", "League of Leagues Status", status_msg)

def check_client_version(icon=None, item=None):
    """Check for updates and provide a link to download if newer version available."""
    print("Checking for client updates...")
    
    # Use a direct, simple approach for the update check
    def do_version_check():
        try:
            resp = requests.get(VERSION_URL, timeout=10)
            print(f"Version check response: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                version = data.get('version', 'Unknown')
                print(f"Server version: {version}")
                
                # Create a simpler dialog directly
                create_update_dialog(version, DOWNLOAD_URL)
            else:
                print(f"Version check error: {resp.status_code}")
                messagebox.showerror("Update Check", f"Failed to check for updates. Server returned error: {resp.status_code}")
        except Exception as e:
            print(f"Version check failed: {e}")
            traceback.print_exc()
            messagebox.showerror("Update Check", f"Failed to check for updates: {str(e)}")
    
    # Schedule the check on the main thread
    threading.Thread(target=do_version_check).start()

def create_update_dialog(version, download_url):
    """Create a simpler update dialog with direct Tkinter calls."""
    print(f"Creating update dialog for version {version}")
    
    try:
        # Force a new Tk root specifically for this dialog
        update_root = tk.Tk()
        update_root.title("League of Leagues Update")
        update_root.geometry("400x200")
        update_root.resizable(False, False)
        
        # Make sure it's visible and on top
        update_root.attributes('-topmost', True)
        update_root.focus_force()
        
        # Center the window
        update_root.update_idletasks()
        width = 400
        height = 200
        x = (update_root.winfo_screenwidth() // 2) - (width // 2)
        y = (update_root.winfo_screenheight() // 2) - (height // 2)
        update_root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Layout
        frame = tk.Frame(update_root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=f"League of Leagues v{version} is available.", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        link_frame = tk.Frame(frame)
        link_frame.pack(fill=tk.X, pady=10)
        
        link_label = tk.Label(link_frame, text="Download:", anchor=tk.W)
        link_label.pack(side=tk.LEFT)
        
        link = tk.Label(link_frame, text=download_url, fg="blue", cursor="hand2")
        link.pack(side=tk.LEFT, padx=5)
        link.bind("<Button-1>", lambda e: webbrowser.open(download_url))
        
        tk.Label(frame, text="After downloading the new version, close this application and run the new version.", 
                 wraplength=360).pack(fill=tk.X, pady=10)
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Open Download Page", 
                  command=lambda: webbrowser.open(download_url)).pack(side=tk.LEFT)
        
        # Close button
        tk.Button(btn_frame, text="Close", 
                  command=update_root.destroy).pack(side=tk.RIGHT)
        
        # Start the dialog's main loop
        update_root.mainloop()
        
    except Exception as e:
        print(f"Error creating update dialog: {e}")
        traceback.print_exc()

def show_update_dialog(version, download_url):
    """Show information about updates with a link to download."""
    global root, dialog_active
    
    print(f"Showing update dialog for version {version}")
    
    if dialog_active:
        print(f"Dialog already active, skipping update dialog")
        return
        
    try:
        dialog_active = True
        ensure_root_window()
        
        # Create a new toplevel window for the update dialog
        dialog = tk.Toplevel(root)
        dialog.title("League of Leagues Update")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # Make this dialog modal
        dialog.transient(root)
        dialog.grab_set()
        
        # Center the window
        dialog.update_idletasks()
        width = 400
        height = 200
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make sure dialog is visible and on top
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        dialog.update()
        
        # Layout
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=f"League of Leagues v{version} is available.", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        link_frame = tk.Frame(frame)
        link_frame.pack(fill=tk.X, pady=10)
        
        link_label = tk.Label(link_frame, text="Download:", anchor=tk.W)
        link_label.pack(side=tk.LEFT)
        
        link = tk.Label(link_frame, text=download_url, fg="blue", cursor="hand2")
        link.pack(side=tk.LEFT, padx=5)
        link.bind("<Button-1>", lambda e: webbrowser.open(download_url))
        
        tk.Label(frame, text="After downloading the new version, close this application and run the new version.", 
                 wraplength=360).pack(fill=tk.X, pady=10)
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Open Download Page", 
                  command=lambda: webbrowser.open(download_url)).pack(side=tk.LEFT)
        
        # Make sure dialog closes properly and cleans up
        def on_close():
            dialog.destroy()
            global dialog_active
            dialog_active = False
        
        tk.Button(btn_frame, text="Close", command=on_close).pack(side=tk.RIGHT)
        
        # Handle window close event
        dialog.protocol("WM_DELETE_WINDOW", on_close)
    except Exception as e:
        print(f"Error showing update dialog: {e}")
        traceback.print_exc()
        dialog_active = False

def quit_application(icon, item):
    """Properly exit the application."""
    print("Quit action triggered")
    
    # Ask for confirmation
    if not show_dialog("yesno", "Confirm Exit", "Are you sure you want to quit?"):
        return
    
    print("Quitting application")
    
    # Clean up resources in reverse order
    try:
        # Stop the tray icon first (important!)
        if icon:
            icon.stop()
        
        # Give a moment for icon to stop
        time.sleep(0.2)
        
        # Exit the application forcefully
        os._exit(0)
    except Exception as e:
        print(f"Error during exit: {e}")
        # Force exit anyway
        os._exit(1)

# --------------------------
# System tray setup
# --------------------------
def create_tray_icon():
    """Create and set up the system tray icon with menu."""
    try:
        icon_image = create_tray_image()
        icon = pystray.Icon('lol', icon_image, 'League of Leagues Client')
        
        icon.menu = pystray.Menu(
            pystray.MenuItem('Register', register_action),
            pystray.MenuItem('Join Game', join_game_action),
            pystray.MenuItem('Check Status', check_status_action),
            pystray.MenuItem('Check for Updates', check_client_version),
            pystray.MenuItem('Quit', quit_application)
        )
        
        return icon
    except Exception as e:
        print(f"Error creating tray icon: {e}")
        traceback.print_exc()
        return None

def create_tray_image():
    """Create an image for the system tray icon using the same icon as the executable.
    Works on both Windows and macOS."""
    try:
        # Determine icon paths based on platform and execution context
        icon_paths = []
        
        # Get base directory where the executable or script is located
        if getattr(sys, 'frozen', False):
            # Running as a bundled executable
            if sys.platform == 'darwin':  # macOS
                # For Mac .app bundles
                bundle_dir = os.path.dirname(sys.executable)
                if '.app/Contents/MacOS' in bundle_dir:
                    # Standard macOS app bundle structure
                    resources_dir = bundle_dir.replace('MacOS', 'Resources')
                    icon_paths.extend([
                        os.path.join(resources_dir, 'icon.icns'),
                        os.path.join(resources_dir, 'icon.ico'),
                        os.path.join(resources_dir, 'icon.png'),
                    ])
                else:
                    # Fallback for non-standard bundle
                    icon_paths.extend([
                        os.path.join(bundle_dir, 'icon.icns'),
                        os.path.join(bundle_dir, 'icon.ico'),
                        os.path.join(bundle_dir, 'icon.png'),
                    ])
            else:  # Windows/Linux
                exe_dir = os.path.dirname(sys.executable)
                icon_paths.extend([
                    os.path.join(exe_dir, 'icon.ico'),
                    os.path.join(exe_dir, 'icon.png'),
                    # Also check common subdirectories
                    os.path.join(exe_dir, 'assets', 'icon.ico'),
                    os.path.join(exe_dir, 'resources', 'icon.ico'),
                ])
        else:
            # Running as a script
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_paths.extend([
                os.path.join(script_dir, 'icon.ico'),
                os.path.join(script_dir, 'icon.png'),
                os.path.join(script_dir, 'icon.icns'),
                os.path.join(script_dir, 'assets', 'icon.ico'),
                os.path.join(script_dir, 'resources', 'icon.ico'),
            ])
        
        # Add current working directory as fallback
        current_dir = os.getcwd()
        icon_paths.extend([
            os.path.join(current_dir, 'icon.ico'),
            os.path.join(current_dir, 'icon.png'),
            os.path.join(current_dir, 'icon.icns'),
        ])
        
        # Remove any duplicates from the paths list
        icon_paths = list(dict.fromkeys(icon_paths))
        
        # Try each path until we find a valid icon
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                print(f"Found icon at: {icon_path}")
                try:
                    img = Image.open(icon_path)
                    # Convert to RGBA if it's not already
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    # Ensure it's the right size for system tray (64x64)
                    if img.size != (64, 64):
                        # Use LANCZOS for high-quality resizing
                        try:
                            img = img.resize((64, 64), Image.LANCZOS)  # For older PIL
                        except AttributeError:
                            img = img.resize((64, 64), Image.Resampling.LANCZOS)  # For newer PIL
                    return img
                except Exception as img_err:
                    print(f"Error loading {icon_path}: {img_err}")
                    continue
        
        # If we reach here, we didn't find a usable icon file
        print("No usable icon file found, creating fallback icon")
        raise FileNotFoundError("Icon file not found")
        
    except Exception as e:
        print(f"Using fallback icon: {e}")
        # Create a fallback icon that works on both platforms
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))  # Transparent background
        dc = ImageDraw.Draw(img)
        
        # Draw a colored background
        dc.rectangle((2, 2, 62, 62), fill=(72, 61, 139), outline=(255, 255, 255), width=2)
        
        # Add "LoL" text if possible
        try:
            # Try common fonts available on both platforms
            font_options = ["Arial", "Helvetica", "Tahoma", "Verdana", "Times New Roman"]
            font = None
            
            for font_name in font_options:
                try:
                    font = ImageFont.truetype(font_name, 24)
                    break
                except:
                    continue
                    
            if font:
                text = "LoL"
                # Handle different PIL versions (compatible with older and newer)
                try:
                    # Newer Pillow versions
                    if hasattr(font, 'getbbox'):
                        bbox = font.getbbox(text)
                        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    # Older Pillow versions
                    elif hasattr(dc, 'textsize'):
                        text_width, text_height = dc.textsize(text, font=font)
                    else:
                        text_width, text_height = 30, 20
                        
                    position = ((64 - text_width) // 2, (64 - text_height) // 2)
                    dc.text(position, text, fill=(255, 255, 255), font=font)
                except Exception as text_error:
                    print(f"Error rendering text: {text_error}")
                    dc.rectangle((20, 20, 44, 44), fill=(255, 255, 255))
            else:
                # Fallback if no font found - simple white square
                dc.rectangle((20, 20, 44, 44), fill=(255, 255, 255))
        except Exception as font_error:
            print(f"Error with font: {font_error}")
            # Ultimate fallback - just a plain square
            dc.rectangle((20, 20, 44, 44), fill=(255, 255, 255))
            
        return img


# --------------------------
# LCU Connection setup
# --------------------------

# Setup connector handlers
def setup_connector(conn):
    """Set up the connector handlers."""
    
    @conn.ready
    async def connect(connection):
        global summoner_name, summoner_tag, region, is_ready, current_phase
        print("[DEBUG] Connector ready handler invoked")
        is_ready = True
        
        # Get initial phase state
        try:
            resp = await connection.request('GET', '/lol-gameflow/v1/gameflow-phase')
            current_phase = await resp.json()
            print(f"[INITIAL PHASE] {current_phase}")
        except Exception as e:
            print(f"Failed to get initial phase: {e}")
            current_phase = None
        
        # Fetch summoner info
        await fetch_summoner_info(connection)
        
    @conn.ws.register('/lol-summoner/v1/current-summoner', event_types=('UPDATE', 'CREATE'))
    async def on_summoner_update(connection, event):
        global summoner_name, summoner_tag, region
        
        try:
            # Try to get information from event data
            if event.data:
                summoner_name = event.data.get('gameName')
                summoner_tag = event.data.get('tagLine')
                
                # If we didn't get the info, try to get it directly
                if not summoner_name or not summoner_tag:
                    try:
                        # Try direct request to the endpoint
                        resp = await connection.request('GET', '/lol-summoner/v1/current-summoner')
                        if resp.status == 200:
                            summoner_data = await resp.json()
                            summoner_name = summoner_data.get('gameName')
                            summoner_tag = summoner_data.get('tagLine')
                    except Exception as e:
                        print(f"Error getting summoner data: {e}")
                        
                # Try to get region information 
                try:
                    region_resp = await connection.request('GET', '/riotclient/region-locale')
                    if region_resp.status == 200:
                        region_data = await region_resp.json()
                        region = region_data.get('region', '').upper()
                except Exception as e:
                    print(f"Error getting region data: {e}")
                    
                print(f'Summoner updated: {summoner_name}#{summoner_tag} Region: {region}')
        except Exception as e:
            print(f"Error in summoner update handler: {e}")
    
    @conn.ws.register('/lol-gameflow/v1/gameflow-phase')
    async def on_gameflow_phase(connection, event):
        global current_phase
        try:
            # The phase might come in event.data or we might need to fetch it
            if isinstance(event.data, str):
                current_phase = event.data
            else:
                # If not a direct string, try to get current phase
                resp = await connection.request('GET', '/lol-gameflow/v1/gameflow-phase')
                current_phase = await resp.json()
            
            print(f"[GAMEFLOW] Phase changed to: {current_phase}")
                
        except Exception as e:
            print(f"[GAMEFLOW ERROR] {str(e)}")
            current_phase = None
    
    return conn

async def fetch_summoner_info(connection):
    global summoner_name, summoner_tag, region
    
    try:
        # Try to get summoner info
        resp = await connection.request('GET', '/lol-summoner/v1/current-summoner')
        if resp.status == 200:
            data = await resp.json()
            summoner_name = data.get('gameName')
            summoner_tag = data.get('tagLine')
            
            # Try to get region
            try:
                region_resp = await connection.request('GET', '/riotclient/region-locale')
                if region_resp.status == 200:
                    region_data = await region_resp.json()
                    region = region_data.get('region', '').upper()
            except Exception:
                pass
                
            print(f'Fetched summoner info: {summoner_name}#{summoner_tag} Region: {region}')
            return True
    except Exception as e:
        print(f"Error fetching summoner info: {e}")
    return False

# --------------------------
# Application entry point
# --------------------------
def main():
    global app_icon, root, connector
    
    try:
        # Initialize UI
        root = ensure_root_window()
        
        # Create and run the system tray icon
        app_icon = create_tray_icon()
        if not app_icon:
            print("Failed to create system tray icon, exiting.")
            return
        
        # Initialize LCU connector in the main thread
        connector = Connector()
        setup_connector(connector)
        
        # Attempt authentication if we have stored credentials
        config_data = load_config()
        raw_id = config_data.get('discord_id') if isinstance(config_data, dict) else config_data
        
        if raw_id:
            try:
                auth_success = authenticate(raw_id)
                if auth_success:
                    print("Successfully authenticated with stored credentials")
                else:
                    print("Authentication failed with stored credentials")
                    delete_config()
            except Exception as e:
                print(f"Error during authentication: {e}")
        
        # Start connector in a separate thread
        def start_connector():
            try:
                print("Starting LCU connector...")
                # Try to start the connector with retries
                max_attempts = 30
                attempts = 0
                
                while attempts < max_attempts:
                    try:
                        connector.start()
                        print("[DEBUG] Connector.start() succeeded")
                        break
                    except Exception as e:
                        attempts += 1
                        print(f"[DEBUG] LCU connection failed: {e}, retrying in 10 seconds... (Attempt {attempts}/{max_attempts})")
                        time.sleep(10)
                
                if attempts >= max_attempts:
                    print("Failed to connect to the League client after multiple attempts.")
            except Exception as e:
                print(f"Error starting connector: {e}")
                traceback.print_exc()
        
        # Start the connector in a background thread
        threading.Thread(target=start_connector, daemon=True).start()
        
        # Set up a Tkinter timer to process events
        def process_events():
            try:
                if root and root.winfo_exists():
                    root.update()
                root.after(100, process_events)  # Schedule again
            except Exception as e:
                print(f"Error processing events: {e}")
        
        # Start processing events
        root.after(100, process_events)
        
        # Run the system tray icon (this blocks the main thread)
        print("Starting system tray icon...")
        app_icon.run()
        
    except Exception as e:
        print(f"Critical error in main: {e}")
        traceback.print_exc()
    finally:
        # Ensure clean exit
        print("Exiting application")
        if root and root.winfo_exists():
            root.destroy()
        os._exit(0)

if __name__ == '__main__':
    main()