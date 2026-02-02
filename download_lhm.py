"""
Downloads the correct LibreHardwareMonitorLib DLL and dependencies from NuGet.
"""

import urllib.request
import zipfile
import os

PACKAGES = [
    ("LibreHardwareMonitorLib", "0.9.4", "netstandard2.0"),
    ("HidSharp", "2.1.0", "netstandard2.0"),
    # These need runtime assemblies, not reference assemblies
    ("System.IO.FileSystem.AccessControl", "5.0.0", "net461"),
    ("System.Security.AccessControl", "5.0.0", "net461"),
    ("System.Security.Principal.Windows", "5.0.0", "net461"),
    ("Microsoft.Win32.Registry", "5.0.0", "net461"),
]

def download_package(name, version, framework, app_dir):
    url = f"https://www.nuget.org/api/v2/package/{name}/{version}"
    zip_path = os.path.join(app_dir, "temp_pkg.zip")

    print(f"  Downloading {name} {version}...")
    urllib.request.urlretrieve(url, zip_path)

    extracted = False
    with zipfile.ZipFile(zip_path, 'r') as z:
        for entry in z.namelist():
            # Skip reference assemblies (ref/) - we need runtime assemblies (lib/ or runtimes/)
            if "/ref/" in entry:
                continue
            # Look for lib/{framework}/ or runtimes/win/lib/{framework}/
            if (f"lib/{framework}" in entry or f"runtimes/win/lib" in entry) and entry.endswith(".dll"):
                dll_name = os.path.basename(entry)
                target = os.path.join(app_dir, dll_name)
                with z.open(entry) as src, open(target, 'wb') as dst:
                    dst.write(src.read())
                print(f"    Extracted: {dll_name}")
                extracted = True

    # If no runtime assembly found, try netstandard2.0 in lib folder
    if not extracted:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for entry in z.namelist():
                if "/ref/" in entry:
                    continue
                if "lib/netstandard2.0" in entry and entry.endswith(".dll"):
                    dll_name = os.path.basename(entry)
                    target = os.path.join(app_dir, dll_name)
                    with z.open(entry) as src, open(target, 'wb') as dst:
                        dst.write(src.read())
                    print(f"    Extracted: {dll_name}")

    os.remove(zip_path)

def download_and_extract():
    app_dir = os.path.dirname(os.path.abspath(__file__))

    # Clean up old DLLs first
    print("Cleaning up old DLLs...")
    for f in os.listdir(app_dir):
        if f.endswith(".dll"):
            os.remove(os.path.join(app_dir, f))
            print(f"  Removed: {f}")

    print("\nDownloading LibreHardwareMonitor and dependencies from NuGet...\n")

    for name, version, framework in PACKAGES:
        download_package(name, version, framework, app_dir)

    print("\nDone! Now restart theme_editor.py as Administrator.")

if __name__ == "__main__":
    download_and_extract()
