"""Setup script for aba package with custom build command for React frontend."""

import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithFrontend(build_py):
    """Custom build command that builds the React frontend before packaging."""

    def run(self):
        """Run the build, including the React frontend."""
        # Build the React frontend
        frontend_dir = Path(__file__).parent / "web-ui"

        if not frontend_dir.exists():
            print("Warning: web-ui directory not found, skipping frontend build")
        else:
            print("Building React frontend...")

            # Check if npm is available
            try:
                subprocess.run(["npm", "--version"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Error: npm not found. Please install Node.js and npm to build the frontend.")
                print("Skipping frontend build. The web interface may not work correctly.")
                super().run()
                return

            # Install dependencies if node_modules doesn't exist
            if not (frontend_dir / "node_modules").exists():
                print("Installing npm dependencies...")
                try:
                    subprocess.run(
                        ["npm", "install"],
                        cwd=frontend_dir,
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Error installing npm dependencies: {e}")
                    sys.exit(1)

            # Run the build
            try:
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=frontend_dir,
                    check=True
                )
                print("Frontend build complete!")
            except subprocess.CalledProcessError as e:
                print(f"Error building frontend: {e}")
                sys.exit(1)

        # Continue with the standard build
        super().run()


# Use setup() with cmdclass to register the custom build command
setup(
    cmdclass={
        'build_py': BuildWithFrontend,
    }
)
