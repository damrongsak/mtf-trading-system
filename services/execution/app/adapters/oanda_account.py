from oandapyV20 import API
import oandapyV20.endpoints.accounts as accounts
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class OandaAccountAdapter:
    def __init__(self):
        self.client = API(access_token=settings.OANDA_API_KEY, environment=settings.OANDA_ENV)
        self.account_id = settings.OANDA_ACCOUNT_ID

    def get_summary(self):
        """
        Fetch account summary including NAV and margin availability.
        """
        try:
            r = accounts.AccountSummary(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('account', {})
        except Exception as e:
            logger.error(f"Failed to fetch account summary: {e}")
            raise e

    def get_details(self):
        """
        Fetch full account details.
        """
        try:
            r = accounts.AccountDetails(accountID=self.account_id)
            self.client.request(r)
            return r.response.get('account', {})
        except Exception as e:
            logger.error(f"Failed to fetch account details: {e}")
            raise e
