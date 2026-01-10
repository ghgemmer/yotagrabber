#!/usr/bin/env python3
"""
Fetch vehicle inventory using yotagrabber

Usage:
    python fetch_vehicle.py <make> <model>

Examples:
    python fetch_vehicle.py lexus rz        # Fetch Lexus RZ inventory
    python fetch_vehicle.py lexus nx        # Fetch Lexus NX inventory
    python fetch_vehicle.py toyota tacoma   # Fetch Toyota Tacoma inventory
    python fetch_vehicle.py toyota rav4     # Fetch Toyota RAV4 inventory

Supported Makes:
    - toyota
    - lexus

Common Lexus Models:
    nx, rx, tx, es, gx, lx, ux, is, ls, lc, rc, rz

Common Toyota Models:
    camry, tacoma, tundra, rav4hybrid, rav4, corolla, corollacross, 4runner, highlander, grandhighlander, sienna, avalon, prius, priusprime
"""
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def print_usage():
    print(__doc__)

def main():
    if len(sys.argv) < 3:
        print_usage()
        print("\nError: Please provide both make and model as arguments.")
        sys.exit(1)

    make = sys.argv[1].lower()
    model = sys.argv[2].lower()

    # Validate make
    supported_makes = ['toyota', 'lexus']
    if make not in supported_makes:
        print(f"Error: Unsupported make '{make}'. Supported makes are: {', '.join(supported_makes)}")
        sys.exit(1)

    # Set environment variables
    os.environ['VEHICLE_MAKE'] = make
    os.environ['MODEL'] = model

    print("=" * 80)
    print(f"FETCHING {make.upper()} {model.upper()} VEHICLE INVENTORY")
    print("=" * 80)
    print(f"Vehicle Make: {make}")
    print(f"Vehicle Model: {model}")
    print()

    # Import the vehicles module from yotagrabber
    try:
        from yotagrabber import vehicles
        
        print("Starting inventory fetch...")
        print("This may take several minutes depending on the model and inventory size.")
        print()

        vehicles.update_vehicles()

        # Determine output directory
        if make == 'lexus':
            output_dir = Path(f"output/lexus")
        else:
            output_dir = Path(f"output")

        print("\n" + "=" * 80)
        print("INVENTORY FETCH COMPLETED!")
        print("*" * 80)
        print(f"Output files created in: {output_dir}/")
        print(f"    - {model}_Lastraw.parquet (current raw inventory data)")
        print(f"    - {model}.csv (processed inventory with pricing)")
        print(f"    - {model}_LastStatusInfo.json (fetch status)")
        print(f"    - {model}_ChangeHistory.csv (change tracking)")
        print(f"    - {model}_YYYY_Sold.csv (sold vehicles by year)")
        print()
        print(f"Full path: {output_dir.absolute()}/")

    except KeyboardInterrupt:
        print("\nInventory fetch cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred during inventory fetch:")
        print(f"    {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
