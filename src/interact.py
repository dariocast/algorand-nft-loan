import json

from beaker import sandbox
from beaker.client import ApplicationClient

from src.contract import BorrowMyNFT

# Get the sandbox accounts
accounts = sandbox.get_accounts()
contract_owner_account = accounts.pop()
borrower_account = accounts.pop()
lender_account = accounts.pop()
print( f"Contract owner's address: {contract_owner_account.address}", sep = "\n\n")
print( f"Borrower's address:  {borrower_account.address}", sep = "\n\n")
print(f"Lender's address: {lender_account.address}", sep = "\n\n")
# Set up the algod client, automatic configuration
client = sandbox.get_algod_client()
#Create instance of the BorrowMyNFT contract
app = BorrowMyNFT()
#Create the Application Client containing the algod client and the app
app_client = ApplicationClient(client, app, signer=contract_owner_account.signer)
def demo():
    sp = client.suggested_params()
    print(f"Suggested flat fee is {sp.min_fee} microAlgos")
    print("### CREATE AND INITIALIZE CONTRACT ### \n")
    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    # app_id, app_addr, txid = app_client.create(event_price=1 * consts.algo)
    print(f"Current Application state: {app_client.get_application_state()}\n")
    print(
        f"""Deployed app in txid {txid}
        App ID: {app_id}
        Address: {app_addr}
        """)
    print(f"Account local state: {app_client.get_account_state()}, \n")
    # Show Application Account information
    print("### APPLICATION ACCOUNT INFO: \n")
    app_account_info = json.dumps(app_client.get_application_account_info(), indent=4)
    print(app_account_info)

if __name__ == "__main__":
    demo()
