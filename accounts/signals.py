# accounts/signals.py
# Signals are defined in accounts/models.py via @receiver decorator.
# This file exists so accounts/apps.py can import it explicitly via:
#   import accounts.signals
# to ensure the signal handlers are connected at app startup.
