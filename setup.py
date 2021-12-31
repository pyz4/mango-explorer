from setuptools import setup, find_packages

setup(
    name="mango-explorer",
    # name="win",
    # version="0.3",
    # description="Main Repo",
    packages=[pkg for pkg in find_packages(".") if pkg.startswith("mango")],
    include_package_data=True,
    # entry_points={"console_scripts": ["dash=win.dash.cli:main"]},
)
