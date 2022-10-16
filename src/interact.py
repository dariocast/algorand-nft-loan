import json

from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.future import transaction
from beaker import sandbox, consts
from beaker.client import ApplicationClient, LogicException

from src.utils import create_default_nft
from src.contract import BorrowMyNFT
from src.utils import nft_metadata_github_url



#nft_metadata_github_url = "https://raw.githubusercontent.com/dariocast/algorand-nft-loan/main/assets/nft_metadata.json"

# Get the sandbox accounts
accounts = sandbox.get_accounts()
lender_account = accounts.pop()
borrower_account = accounts.pop()
contract_owner_account = accounts.pop()
print("### SET UP SCENARIO ### \n")
print(f"Contract owner's address: {contract_owner_account.address}", sep = "\n\n")
print(f"Borrower's address:  {borrower_account.address}", sep = "\n\n")
print(f"Lender's address: {lender_account.address} \n")
# Set up the algod client, automatic configuration
client = sandbox.get_algod_client()
#Create instance of the BorrowMyNFT contract
app = BorrowMyNFT()
# Create the Application client for the contract owner containing both an algod client and my app
app_client = ApplicationClient(
    client,
    app,
    signer=contract_owner_account.signer)
def demo():
    ############# TESTING SCENARIO #############
    # Best scenario where:
    #   - FIST PART: Contract Creation Step
    #   - SECOND PART: Set up of the NFT and offer Step
    #   - THIRD PART: Bid Step
    #   - FOURTH PART: Payment Step

    # FIRST PART
    print("### BEST SCENARIO ### \n")
    print(f"{contract_owner_account.address} is creating the contract...\n")
    # print("Creating the contract..\n")
    # Create the application on chain, set the app id, app address and tx id for the app client
    app_id, app_addr, txid = app_client.create()
    print("Contract created!")
    print(
        f"""Deployed app in Txid {txid}
        App ID: {app_id}
        Address: {app_addr}
        """)
    # Fund the contract for minimum balance
    app_client.fund(1 * consts.algo)
    print(f"Contract Balance: {client.account_info(app_addr).get('amount')} microAlgos \n")

    result = app_client.call(app.health)
    print(f"Health: {result.return_value} \n")

    # See the application account state
    app_state = app_client.call(app.read_state)
    print(f"Account state: {app_state.return_value}")

    # Read state from owner account
    print("Reading state from owner account")
    state = app_client.call(app.read_state)
    print(f"State: {state.return_value} \n")

    # SECOND PART

    # Create the Application client for the borrower containing both an algod client and my app
    app_client_borrower = app_client.prepare(
        signer=borrower_account.signer
    )
    print("Creating NFT...")
    # Create the NFT
    asset_id = create_default_nft(
        sandbox.get_algod_client(),
        borrower_account.private_key,
        borrower_account.address,
        "G3 NFT@arc3",
        "G3",
        nft_metadata_github_url)

    #  Providing NFT info and payment to allow contract opt in
    print("Send NFT info and payment to allow contract opt in")

    # Get suggested params from the client
    sp = client.suggested_params()
    payment_txn = TransactionWithSigner(
        txn=transaction.PaymentTxn(
            borrower_account.address,
            sp,
            app_addr,
            100*consts.milli_algo
        ),
        signer=borrower_account.signer,
    )
    sp.flat_fee = True
    sp.fee = 2000
    # Trigger the NFT optin to the contract
    app_client_borrower.call(
        app.provide_access_to_nft,
        suggested_params=sp,
        nft=asset_id,
        payment=payment_txn,
    )
    print("Provided access to NFT\n")

    # Set offer
    print("Setting offer...")

    # Get suggested params from the client
    sp = client.suggested_params()
    # Construct TransactionWithSigner
    asset_xfer_txn = TransactionWithSigner(
        txn=transaction.AssetTransferTxn(
            sender=borrower_account.address,
            receiver=app_addr,
            sp=sp,
            index=asset_id,
            amt=1,
        ),
        signer=borrower_account.signer,
    )
    # Set up the offer
    app_client_borrower.call(
        app.set_offer,
        suggested_params=sp,
        asset_xfer=asset_xfer_txn,
        loan_threshold=1000,
        auction_period=100,
        payback_deadline=100,
    )
    print("Offer set!\n")

    # THIRD PART (Bidding Part)
    # Create the Application client for the lender containing both an algod client and my app
    app_client_lender = app_client.prepare(
        signer=lender_account.signer
    )

    # FOURTH PART (Payment Part)

    # Show Application Account information
    # print("### APPLICATION ACCOUNT INFO: \n")
    # app_account_info = json.dumps(app_client.get_application_account_info(), indent=4)
    # print(app_account_info)

    print("### END ###\n")


if __name__ == "__main__":
    demo()
