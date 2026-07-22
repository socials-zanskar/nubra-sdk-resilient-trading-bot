"""
A complete, resilient trading script with the Nubra Python SDK.

This end-to-end example puts all the error handling together:

  login -> look up instrument -> place order -> check order status

Every step handles its own failures, uses logging instead of print,
and the whole script has one final safety net so it never crashes
with a raw traceback.

Start here if you want a realistic template for your own bot.
"""

import logging
import sys
import time

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.interceptor.errors import (
    NubraHttpError,
    UnauthorizedError,
    BadRequestError,
    ServerError,
    RetryLimitExceeded,
    NubraValidationError,
)

# Logging setup: INFO shows your messages AND the SDK's own messages
# (reconnects, requests, etc.). Switch to DEBUG when investigating a problem.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("my-bot")


def login():
    """Step 1: log in. Returns the SDK client, or None if login failed."""
    try:
        nubra = InitNubraSdk(env=NubraEnv.PROD)
        log.info("Logged in successfully.")
        return nubra
    except ValueError as e:
        # The login flow raises ValueError for OTP/MPIN problems,
        # e.g. "Maximum OTP attempts exceeded."
        log.error("Login failed: %s", e)
        return None


def find_instrument(nubra, symbol):
    """Step 2: look up the instrument so we get its refId."""
    instruments = InstrumentData(nubra)
    result = instruments.get_instrument_by_symbol(symbol)

    # Lookups do not raise -- they return a {"msg": ...} dict when
    # the symbol is not found. Always check for that.
    if isinstance(result, dict) and "msg" in result:
        log.error("Instrument lookup failed for '%s': %s", symbol, result["msg"])
        return None

    log.info("Found %s -> refId %s", symbol, result.ref_id)
    return result


def place_order(trader, ref_id, qty):
    """Step 3: place a market order, handling every error type."""
    order = {
        "refId": ref_id,
        "qty": qty,
        "side": "BUY",
        "deliveryType": "IDAY",
        "priceType": "MARKET",
        "validityType": "DAY",
    }
    try:
        response = trader.create_order(order)
        log.info("Order accepted: %s", response)
        return response

    except NubraValidationError as e:
        log.error("Order payload invalid, fix the fields: %s", e.validation_error)
    except UnauthorizedError:
        log.error("Session expired and re-login failed. Delete auth_data.db and restart.")
    except BadRequestError as e:
        log.error("Order rejected by the API: %s", e)
    except (ServerError, RetryLimitExceeded) as e:
        log.error("Temporary problem (server/network): %s", e)
        log.error("Check your orders before retrying to avoid a duplicate!")
    return None


def check_order_status(trader, wait_seconds=2, checks=3):
    """Step 4: poll our orders a few times to see the latest status."""
    for i in range(checks):
        try:
            orders = trader.orders()
            log.info("Check %d/%d: you have %d orders.", i + 1, checks, len(orders or []))
            return orders
        except (ServerError, RetryLimitExceeded) as e:
            # Reading is safe to retry.
            log.warning("Could not fetch orders (%s), retrying in %ss...", e, wait_seconds)
            time.sleep(wait_seconds)
    log.error("Gave up fetching order status after %d attempts.", checks)
    return None


def main():
    nubra = login()
    if nubra is None:
        sys.exit(1)

    trader = NubraTrader(nubra)

    instrument = find_instrument(nubra, "RELIANCE")
    if instrument is None:
        sys.exit(1)

    result = place_order(trader, ref_id=instrument.ref_id, qty=1)
    if result is None:
        sys.exit(1)

    check_order_status(trader)
    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    except NubraHttpError as e:
        # Final safety net: any Nubra HTTP error we did not handle above.
        log.error("Unhandled Nubra error: %s", e)
        sys.exit(1)
