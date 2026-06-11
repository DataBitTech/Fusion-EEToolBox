#======================================================
# This software is released under the MIT license:
#
# MIT License
# 
# Copyright (c) 2025 Pal Szabo
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#======================================================

import enum
import sys
import adsk.core

def get_theme() -> str:
    """Determines the current theme for the application.

    Checks the Fusion theme and falls back to OS theme if Fusion theme is not
    recognized or available.

    Returns:
        str: The theme name ('dark-theme' or 'light-theme').
    """
    fusion_theme = get_Fusion_theme()
    return fusion_theme if fusion_theme in ['dark-theme', 'light-theme'] else get_os_theme()


def get_Fusion_theme() -> str:
    """Determines the Fusion application theme.

    Gets the current Fusion theme by checking the user interface theme preference.

    Returns:
        str: The Fusion theme name ('dark-theme' or 'light-theme').
    """
    class UserInterfaceThemes(enum.IntEnum):
        ClassicUserInterfaceTheme = 0
        LightGrayUserInterfaceTheme = 1
        DarkBlueUserInterfaceTheme = 2
        DarkGrayUserInterfaceTheme = 3

    app = adsk.core.Application.get()
    try:
        theme_name = UserInterfaceThemes(app.preferences.generalPreferences.userInterfaceTheme).name
        if "Dark" in theme_name:
            return "dark-theme"
        else:
            return "light-theme"
    except ValueError:
        return "Unknown"


def get_os_theme() -> str:
    """Get the OS theme (light or dark) - works on Windows, macOS, and Linux.

    Determines the operating system's theme preference by checking system settings.

    Returns:
        str: The OS theme name ('dark-theme' or 'light-theme').
    """
    try:
        # Get the current application instance
        app = adsk.core.Application.get()
        
        # Check the operating system
        if sys.platform == "win32":
            # Windows
            import winreg
            try:
                # Open the registry key for dark mode settings
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                  r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                    # Get the AppsUseLightTheme value (1 = light, 0 = dark)
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return 'light-theme' if value == 1 else 'dark-theme'
            except:
                return 'light-theme'  # Default to light if error
                
        elif sys.platform == "darwin":
            # macOS
            import subprocess
            try:
                # Use defaults command to check dark mode
                result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                                       capture_output=True, text=True)
                return 'dark-theme' if result.stdout.strip() == 'Dark' else 'light-theme'
            except:
                return 'light-theme'  # Default to light if error
                
        else:
            # Linux - check for dark theme in GTK settings
            try:
                import subprocess
                result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                                       capture_output=True, text=True)
                if 'dark-theme' in result.stdout.lower():
                    return 'dark-theme'
                else:
                    return 'light-theme'
            except:
                # Fallback to environment variables
                if os.environ.get('GTK_THEME', '').lower().find('dark-theme') != -1:
                    return 'dark-theme'
                return 'light-theme'  # Default to light
                
    except Exception as e:
        print(f"Error getting OS theme: {e}")
        return 'light-theme'  # Default to light on error