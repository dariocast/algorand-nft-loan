from beaker import sandbox, consts
from beaker.client import ApplicationClient

from src.contract import BorrowMyNFT

client = sandbox.get_algod_client()
accounts = sandbox.get_accounts()

contract_owner_account = accounts.pop()
borrower_account = accounts.pop()
lender_account = accounts.pop()

# Create instance of the BorrowMyNFT contract
app = BorrowMyNFT()

# Create an Application client for event creator containing both an algod client and the app
app_client = ApplicationClient(client, app, signer=contract_owner_account.signer)


def deploy_and_call_status():
    print("### CREATE AND INITIALIZE CONTRACT ### \n")
    sp = client.suggested_params()
    app_id, app_addr, txid = app_client.create()
    print(f"Deployed app in txid {txid}")

    # Fund the contract for minimum balance
    app_client.fund(100 * consts.milli_algo)
    print(f"RSVP Balance: {client.account_info(app_addr).get('amount')} microAlgos \n")

    # Opt in mandatory for everyone, contract_owner included
    # app_client.opt_in()
    health = app_client.call(app.health)
    print(f"Health: {health.return_value} \n")

    try:
        app_client.close_out()
        app_client.delete()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    deploy_and_call_status()
